"""
Verification script for CORTEX Wave 6: Temporal Navigation & Snapshotting.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from cortex.engine import CortexEngine
from cortex.engine.ledger import ImmutableLedger
from cortex.engine.snapshots import SnapshotManager


def test_wave6():
    db_path = "test_wave6.db"
    for ext in ["", "-wal", "-shm"]:
        if os.path.exists(db_path + ext):
            os.remove(db_path + ext)

    print("🚀 Initializing Test Engine...")
    engine = CortexEngine(db_path=db_path)
    engine.init_db_sync()

    print("📝 Storing Facts...")
    f1 = engine.store_sync("project-x", "Fact 1: Initial state", fact_type="knowledge")
    f2 = engine.store_sync("project-x", "Fact 2: Second state", fact_type="knowledge")

    # Get tx_ids
    conn = engine._get_sync_conn()
    txs = conn.execute("SELECT id, action FROM transactions ORDER BY id ASC").fetchall()
    print(f"Transactions: {txs}")

    latest_tx = txs[-1][0]
    first_tx = txs[0][0]

    print(f"🕰 Reconstructing state at TX #{first_tx}...")
    state1 = engine.reconstruct_state_sync(first_tx, project="project-x")
    print(f"State 1 size: {len(state1)}")
    for f in state1:
        print(f"  - {f.content}")
    assert len(state1) == 1
    assert "Initial state" in state1[0].content

    print(f"🕰 Reconstructing state at TX #{latest_tx}...")
    state2 = engine.reconstruct_state_sync(latest_tx, project="project-x")
    print(f"State 2 size: {len(state2)}")
    for f in state2:
        print(f"  - {f.content}")
    assert len(state2) == 2

    print("📸 Testing Snapshot Management...")
    # Create a checkpoint first to have a merkle root
    ledger = ImmutableLedger(conn)
    # Set batch size small for testing
    ImmutableLedger.CHECKPOINT_BATCH_SIZE = 1
    ledger.create_checkpoint_sync()

    root_row = conn.execute(
        "SELECT root_hash FROM merkle_roots ORDER BY id DESC LIMIT 1"
    ).fetchone()
    merkle_root = root_row[0] if root_row else "TEST_ROOT"

    import asyncio
    sm = SnapshotManager(db_path=db_path)
    snap = asyncio.run(sm.create_snapshot("test_snap", latest_tx, merkle_root))
    print(f"Snapshot created: {snap.name} at {snap.path}")

    snaps = asyncio.run(sm.list_snapshots())
    print(f"Snapshots found: {[s.name for s in snaps]}")
    assert len(snaps) >= 1
    assert snaps[0].name == "test_snap"

    print("🔙 Restoring Snapshot...")
    asyncio.run(sm.restore_snapshot(snap.tx_id))

    print("✅ Wave 6 Verification Successful!")
    engine.close()

    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)
    # Cleanup snapshot dir if empty or for this test
    # (Leaving it for now as it's in a specific test_wave6.db parent dir)


if __name__ == "__main__":
    test_wave6()
