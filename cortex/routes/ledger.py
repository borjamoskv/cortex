"""
CORTEX v4.0 - Ledger Router.
Cryptographic integrity verification and checkpointing.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from cortex.auth import AuthResult, require_permission
from cortex.engine.ledger import ImmutableLedger
from cortex.models import LedgerReportResponse, CheckpointResponse
from cortex.engine import CortexEngine
from cortex.api_deps import get_engine


class LedgerError(Exception):
    """Base exception for ledger operations."""


class MerkleIntegrityError(LedgerError):
    """Raised when Merkle verification fails."""


logger = logging.getLogger("cortex.api.ledger")
router = APIRouter(prefix="/v1/ledger", tags=["ledger"])


@router.get("/status", response_model=LedgerReportResponse)
async def get_ledger_status(
    auth: AuthResult = Depends(require_permission("admin")),
    engine: CortexEngine = Depends(get_engine),
) -> LedgerReportResponse:
    """Check the cryptographic integrity of the entire ledger."""
    try:
        report = await engine.verify_ledger()
        if not report.get("valid", True):
            raise MerkleIntegrityError(f"Ledger violation: {report.get('violations', [])}")
        return LedgerReportResponse(**report)
    except MerkleIntegrityError as e:
        logger.error("Ledger integrity violation: %s", e)
        raise HTTPException(status_code=409, detail=f"Ledger integrity violation: {str(e)}")
    except Exception as e:
        logger.exception("Ledger integrity check failed")
        raise HTTPException(status_code=500, detail=f"Integrity check failed: {str(e)}")


@router.post("/checkpoint", response_model=CheckpointResponse)
async def create_checkpoint(
    auth: AuthResult = Depends(require_permission("admin")),
    engine: CortexEngine = Depends(get_engine),
) -> CheckpointResponse:
    """Manually trigger a Merkle root checkpoint for recent transactions."""
    try:
        conn = await engine.get_conn()
        ledger = ImmutableLedger(conn)
        cp_id = await ledger.create_checkpoint_async()

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
    engine: CortexEngine = Depends(get_engine),
) -> LedgerReportResponse:
    """Alias for /status - performs full integrity verification."""
    return await get_ledger_status(auth, engine)
