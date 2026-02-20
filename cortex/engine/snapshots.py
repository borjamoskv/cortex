import json
import logging
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import aiosqlite

from cortex.config import DEFAULT_DB_PATH

logger = logging.getLogger("cortex")


@dataclass
class SnapshotRecord:
    """Metadata for a CORTEX snapshot."""

    id: int
    name: str
    path: str
    tx_id: int
    merkle_root: str
    created_at: str
    size_mb: float


class SnapshotManager:
    """
    Manages physical and logical snapshots of the CORTEX database.
    """

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path).expanduser()
        self.snapshot_dir = self.db_path.parent / "snapshots"
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    async def create_snapshot(self, name: str, tx_id: int, merkle_root: str) -> SnapshotRecord:
        """Create a consistent physical snapshot of the current database.

        Args:
            name: Descriptive name for the snapshot.
            tx_id: The latest transaction ID included in this snapshot.
            merkle_root: The Merkle Root of the ledger at this point.

        Returns:
            SnapshotRecord containing metadata.
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cortex_snap_{ts}_{name}.db"
        dest_path = self.snapshot_dir / filename

        # Use VACUUM INTO for a consistent backup of a live database in WAL mode
        async with aiosqlite.connect(str(self.db_path)) as conn:
            try:
                # We must escape the path for the SQL statement
                # SQLite doesn't support parameters for VACUUM INTO
                safe_path = str(dest_path).replace("'", "''")
                await conn.execute(f"VACUUM INTO '{safe_path}'")
                logger.info("Snapshot created via VACUUM INTO: %s", dest_path)
            except (sqlite3.Error, OSError, ValueError) as e:
                logger.error("Snapshot creation failed: %s", e)
                raise

        size_mb = round(dest_path.stat().st_size / (1024 * 1024), 2)

        # We record the metadata in a alongside JSON file
        meta_path = dest_path.with_suffix(".json")
        record = {
            "name": name,
            "tx_id": tx_id,
            "merkle_root": merkle_root,
            "created_at": datetime.now().isoformat(),
            "size_mb": size_mb,
            "path": str(dest_path),
        }

        # Using standard open since it's just a small JSON meta-file
        with open(meta_path, "w") as f:
            json.dump(record, f, indent=2)

        return SnapshotRecord(
            id=0,  # Metadata ID
            name=name,
            path=str(dest_path),
            tx_id=tx_id,
            merkle_root=merkle_root,
            created_at=record["created_at"],
            size_mb=size_mb,
        )

    async def list_snapshots(self) -> list[SnapshotRecord]:
        """List all available snapshots in the snapshot directory."""
        snapshots = []
        for meta_file in self.snapshot_dir.glob("*.json"):
            try:
                # small files, sync is okay
                with open(meta_file) as f:
                    data = json.load(f)
                    # Check if the DB file actually exists
                    db_file = Path(data["path"])
                    if db_file.exists():
                        snapshots.append(
                            SnapshotRecord(
                                id=0,
                                name=data["name"],
                                path=data["path"],
                                tx_id=data["tx_id"],
                                merkle_root=data["merkle_root"],
                                created_at=data["created_at"],
                                size_mb=data["size_mb"],
                            )
                        )
            except (sqlite3.Error, OSError, ValueError) as e:
                logger.warning("Failed to load snapshot metadata from %s: %s", meta_file, e)

        return sorted(snapshots, key=lambda s: s.created_at, reverse=True)

    async def restore_snapshot(self, tx_id: int) -> bool:
        """Restore the database to a specific snapshot state.

        WARNING: This overwrites the current database.
        """
        all_snapshots = await self.list_snapshots()
        snapshots = [s for s in all_snapshots if s.tx_id == tx_id]
        if not snapshots:
            logger.error("No snapshot found for TX %d", tx_id)
            return False

        snap = snapshots[0]
        logger.info("Restoring snapshot from %s", snap.path)

        # Backup current DB before overwrite
        backup_path = self.db_path.with_suffix(".db.bak")
        shutil.copy2(self.db_path, backup_path)

        try:
            shutil.copy2(snap.path, self.db_path)
            # We may need to remove WAL files as well
            for wal_file in self.db_path.parent.glob(f"{self.db_path.name}-*"):
                wal_file.unlink()
            return True
        except (sqlite3.Error, OSError, ValueError) as e:
            logger.error("Failed to restore snapshot: %s", e)
            shutil.copy2(backup_path, self.db_path)
            return False
