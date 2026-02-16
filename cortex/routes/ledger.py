"""
CORTEX v4.0 — Ledger Router.
Cryptographic integrity verification and checkpointing.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from cortex import api_state
from cortex.auth import AuthResult, require_permission
from cortex.ledger import ImmutableLedger
from cortex.models import LedgerReportResponse, CheckpointResponse
from cortex.engine import CortexEngine


class LedgerError(Exception):
    """Base exception for ledger operations."""
    pass


class MerkleIntegrityError(LedgerError):
    """Raised when Merkle verification fails."""
    pass

logger = logging.getLogger("cortex.api.ledger")
router = APIRouter(prefix="/v1/ledger", tags=["ledger"])


@router.get("/status", response_model=LedgerReportResponse)
async def get_ledger_status(
    auth: AuthResult = Depends(require_permission("admin")),
) -> LedgerReportResponse:
    """Check the cryptographic integrity of the entire ledger."""
    try:
        def _verify():
            with api_state.engine.get_connection() as conn:
                ledger = ImmutableLedger(conn)
                report = ledger.verify_integrity()
                if not report["valid"]:
                    raise MerkleIntegrityError(f"Ledger violation: {report['violations']}")
                return report
        
        report = await run_in_threadpool(_verify)
        return LedgerReportResponse(**report)
    except MerkleIntegrityError as e:
        logger.error("Ledger integrity violation: %s", e)
        # We still return the report so the user can see violations, but we log as ERROR
        # Actually, let's keep it consistent with the model.
        raise HTTPException(status_code=409, detail=f"Ledger integrity violation: {str(e)}")
    except Exception as e:
        logger.exception("Ledger integrity check failed")
        raise HTTPException(status_code=500, detail=f"Integrity check failed: {str(e)}")


@router.post("/checkpoint", response_model=CheckpointResponse)
async def create_checkpoint(
    auth: AuthResult = Depends(require_permission("admin")),
) -> CheckpointResponse:
    """Manually trigger a Merkle root checkpoint for recent transactions."""
    try:
        def _checkpoint():
            with api_state.engine.get_connection() as conn:
                ledger = ImmutableLedger(conn)
                return ledger.create_merkle_checkpoint()
        
        cp_id = await run_in_threadpool(_checkpoint)
        
        if cp_id:
            return CheckpointResponse(
                checkpoint_id=cp_id,
                message=f"Merkle checkpoint #{cp_id} created successfully"
            )
        else:
            return CheckpointResponse(
                checkpoint_id=None,
                message="No new transactions to checkpoint or batch size not reached",
                status="no_action"
            )
    except Exception as e:
        logger.exception("Merkle checkpoint creation failed")
        raise HTTPException(status_code=500, detail=f"Checkpoint failed: {str(e)}")


@router.get("/verify", response_model=LedgerReportResponse)
async def verify_ledger(
    auth: AuthResult = Depends(require_permission("admin")),
) -> LedgerReportResponse:
    """Alias for /status — performs full integrity verification."""
    return await get_ledger_status(auth)
