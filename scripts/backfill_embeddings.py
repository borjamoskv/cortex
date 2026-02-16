#!/usr/bin/env python3
"""
CORTEX — Backfill Embeddings for Historical Facts.

Generates vector embeddings for facts that were stored before
sqlite-vec was operational. Uses batch processing with WAL-friendly
chunking to avoid database bloat.

Usage:
    python scripts/backfill_embeddings.py [--db PATH] [--dry-run] [--batch-size N]
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cortex.embeddings import LocalEmbedder  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("backfill")

DEFAULT_DB = Path.home() / ".cortex" / "cortex.db"


def get_unembedded_facts(conn: sqlite3.Connection) -> list[tuple[int, str]]:
    """Find facts without embeddings."""
    cursor = conn.execute("""
        SELECT f.id, f.content
        FROM facts f
        LEFT JOIN fact_embeddings fe ON f.id = fe.fact_id
        WHERE fe.fact_id IS NULL
            AND f.valid_until IS NULL
        ORDER BY f.id
    """)
    return cursor.fetchall()


def backfill(
    db_path: str,
    batch_size: int = 50,
    dry_run: bool = False,
) -> dict:
    """Backfill embeddings for all facts missing them."""
    import sqlite_vec

    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)

    facts = get_unembedded_facts(conn)
    total = len(facts)

    if total == 0:
        logger.info("✅ All facts already have embeddings!")
        conn.close()
        return {"total": 0, "embedded": 0, "skipped": 0}

    logger.info("📊 Found %d facts without embeddings", total)

    if dry_run:
        logger.info("🔍 DRY RUN — would embed %d facts", total)
        conn.close()
        return {"total": total, "embedded": 0, "skipped": 0, "dry_run": True}

    embedder = LocalEmbedder()
    embedded = 0
    skipped = 0
    start = time.time()

    for i in range(0, total, batch_size):
        batch = facts[i : i + batch_size]
        contents = [f[1] for f in batch]
        ids = [f[0] for f in batch]

        try:
            embeddings = embedder.embed_batch(contents)

            for fact_id, embedding in zip(ids, embeddings):
                try:
                    conn.execute(
                        "INSERT INTO fact_embeddings (fact_id, embedding) VALUES (?, ?)",
                        (fact_id, json.dumps(embedding)),
                    )
                    embedded += 1
                except sqlite3.IntegrityError:
                    skipped += 1  # Already exists (race condition)

            conn.commit()
            elapsed = time.time() - start
            rate = embedded / elapsed if elapsed > 0 else 0
            logger.info(
                "  [%d/%d] embedded=%d skipped=%d (%.1f facts/s)",
                min(i + batch_size, total),
                total,
                embedded,
                skipped,
                rate,
            )
        except Exception as e:
            logger.error("  Batch %d failed: %s", i // batch_size, e)
            skipped += len(batch)

    elapsed = time.time() - start
    conn.close()

    logger.info(
        "🎯 Backfill complete: %d embedded, %d skipped in %.1fs", embedded, skipped, elapsed
    )
    return {"total": total, "embedded": embedded, "skipped": skipped, "time": elapsed}


def main():
    parser = argparse.ArgumentParser(description="Backfill CORTEX embeddings")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Database path")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size")
    parser.add_argument("--dry-run", action="store_true", help="Count only, no writes")
    args = parser.parse_args()

    if not Path(args.db).exists():
        logger.error("❌ Database not found: %s", args.db)
        sys.exit(1)

    backfill(args.db, batch_size=args.batch_size, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
