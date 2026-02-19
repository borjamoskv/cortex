import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ActionLevel(str, Enum):
    """Consciousness layer action levels."""

    L1_READ = "L1_READ"
    L2_PLAN = "L2_PLAN"
    L3_EXECUTE = "L3_EXECUTE"
    L4_MUTATE = "L4_MUTATE"


class GatePolicy(str, Enum):
    """Gate enforcement policy."""

    ENFORCE = "enforce"  # Block until approved
    AUDIT_ONLY = "audit"  # Log but don't block
    DISABLED = "disabled"  # Transparent passthrough


class ActionStatus(str, Enum):
    """Status of a pending action."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    EXECUTED = "executed"
    FAILED = "failed"


@dataclass
class PendingAction:
    """An L3 action awaiting operator approval."""

    action_id: str
    level: ActionLevel
    description: str
    command: list[str] | None = None
    project: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    status: ActionStatus = ActionStatus.PENDING
    created_at: float = field(default_factory=time.time)
    approved_at: float | None = None
    executed_at: float | None = None
    hmac_challenge: str = ""
    operator_id: str | None = None
    result: dict[str, Any] | None = None

    def is_expired(self, timeout_seconds: float) -> bool:
        """Check if the action has exceeded its timeout."""
        return time.time() - self.created_at > timeout_seconds

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for API responses and audit log."""
        return {
            "action_id": self.action_id,
            "level": self.level.value,
            "description": self.description,
            "command": self.command,
            "project": self.project,
            "status": self.status.value,
            "created_at": datetime.fromtimestamp(self.created_at, tz=timezone.utc).isoformat(),
            "approved_at": (
                datetime.fromtimestamp(self.approved_at, tz=timezone.utc).isoformat()
                if self.approved_at
                else None
            ),
            "operator_id": self.operator_id,
        }
