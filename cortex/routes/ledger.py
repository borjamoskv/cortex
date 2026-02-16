"""
CORTEX v4.0 - Ledger Router.
Cryptographic integrity verification and checkpointing.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from cortex.api_deps import get_async_engine
from cortex.auth import AuthResult, require_permission
from cortex.engine_async import AsyncCortexEngine
from cortex.models import CheckpointResponse, LedgerReportResponse


class LedgerError(Exception):
    """Base exception for ledger operations."""


class MerkleIntegrityError(LedgerError):
    """Raised when Merkle verification fails."""


logger = logging.getLogger("cortex.api.ledger")
router = APIRouter(prefix="/v1/ledger", tags=["ledger"])


@router.get("/status", response_model=LedgerReportResponse)
async def get_ledger_status(
    auth: AuthResult = Depends(require_permission("admin")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> LedgerReportResponse:
    """Check the cryptographic integrity of all ledgers (Tx and Votes)."""
    try:
        # 1. Verify Transaction Ledger
        tx_report = await engine.verify_ledger()

        # 2. Verify Vote Ledger
        vote_report = await engine.verify_vote_ledger()

        # Merge reports
        combined_valid = tx_report["valid"] and vote_report["valid"]
        combined_violations = tx_report["violations"] + vote_report["violations"]

        if not combined_valid:
            logger.error(f"Ledger violation detected! {len(combined_violations)} issues found.")

        return LedgerReportResponse(
            valid=combined_valid,
            violations=combined_violations,
            tx_checked=tx_report["tx_checked"],
            roots_checked=tx_report["roots_checked"],
            votes_checked=vote_report["votes_checked"],
            vote_checkpoints_checked=vote_report["checkpoints_checked"],
        )
    except Exception as e:
        logger.exception("Ledger integrity check failed")
        raise HTTPException(status_code=500, detail=f"Integrity check failed: {str(e)}")


@router.post("/checkpoint", response_model=CheckpointResponse)
async def create_checkpoint(
    auth: AuthResult = Depends(require_permission("admin")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> CheckpointResponse:
    """Manually trigger a Merkle root checkpoint for recent transactions."""
    try:
        cp_id = await engine.create_checkpoint()

        if cp_id:
            return CheckpointResponse(
                checkpoint_id=cp_id, message=f"Merkle checkpoint #{cp_id} created successfully"
            )
        else:
            return CheckpointResponse(
                checkpoint_id=None,
                message="No new transactions to checkpoint or batch size not reached",
                status="no_action",
            )
    except Exception as e:
        logger.exception("Merkle checkpoint creation failed")
        raise HTTPException(status_code=500, detail=f"Checkpoint failed: {str(e)}")


@router.get("/verify", response_model=LedgerReportResponse)
async def verify_ledger(
    auth: AuthResult = Depends(require_permission("admin")),
    engine: AsyncCortexEngine = Depends(get_async_engine),
) -> LedgerReportResponse:
    """Alias for /status - performs full integrity verification."""
    return await get_ledger_status(auth, engine)
