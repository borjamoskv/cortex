"""
CORTEX v4.0 — SovereignGate API Router.

REST endpoints for remote operator approval of L3 actions.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List

from cortex.auth import require_permission
from cortex.sovereign_gate import (
    get_gate,
    GateError,
    GateExpired,
    GateInvalidSignature,
    GateNotApproved,
)
from cortex.models import (
    GateApprovalRequest,
    GateActionResponse,
    GateStatusResponse,
)

router = APIRouter(prefix="/v1/gate", tags=["sovereign-gate"])


@router.get("/status", response_model=GateStatusResponse)
async def gate_status(
    _ = Depends(require_permission("read")),
):
    """Get the current SovereignGate status."""
    gate = get_gate()
    return GateStatusResponse(**gate.get_status())


@router.get("/pending", response_model=List[GateActionResponse])
async def list_pending(
    _ = Depends(require_permission("read")),
):
    """List all pending L3 actions awaiting approval."""
    gate = get_gate()
    return [
        GateActionResponse(**a.to_dict())
        for a in gate.get_pending()
    ]


@router.post("/{action_id}/approve", response_model=GateActionResponse)
async def approve_action(
    action_id: str,
    request: GateApprovalRequest,
    _ = Depends(require_permission("write")),
):
    """Approve a pending L3 action with HMAC signature."""
    gate = get_gate()
    try:
        gate.approve(
            action_id=action_id,
            signature=request.signature,
            operator_id=request.operator_id or "api",
        )
        action = gate._get_action(action_id)
        return GateActionResponse(**action.to_dict())
    except GateExpired as e:
        raise HTTPException(status_code=410, detail=str(e))
    except GateInvalidSignature as e:
        raise HTTPException(status_code=403, detail=str(e))
    except GateError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{action_id}/deny")
async def deny_action(
    action_id: str,
    _ = Depends(require_permission("write")),
):
    """Deny a pending L3 action."""
    gate = get_gate()
    try:
        gate.deny(action_id, reason="Denied via API")
        return {"status": "denied", "action_id": action_id}
    except GateError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/audit")
async def get_audit_log(
    limit: int = 50,
    _ = Depends(require_permission("read")),
):
    """View the SovereignGate audit log."""
    gate = get_gate()
    return gate.get_audit_log(limit=limit)
