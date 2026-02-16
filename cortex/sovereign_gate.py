"""
CORTEX v4.0 — SovereignGate.

L3 Action Interception Middleware.
Intercepts all L3 (execution-level) actions and requires
cryptographic operator approval before execution.

Resolves the architectural tension between the Fractal Swarm
(80 parallel agents) and the hard limit "NEVER deploy without
confirmation" by providing an enforceable gate.
"""

import hashlib
import hmac
import json
import logging
import os
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("cortex.gate")


# ─── Enums ────────────────────────────────────────────────────────────


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


# ─── Models ───────────────────────────────────────────────────────────


@dataclass
class PendingAction:
    """An L3 action awaiting operator approval."""

    action_id: str
    level: ActionLevel
    description: str
    command: Optional[List[str]] = None
    project: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    status: ActionStatus = ActionStatus.PENDING
    created_at: float = field(default_factory=time.time)
    approved_at: Optional[float] = None
    executed_at: Optional[float] = None
    hmac_challenge: str = ""
    operator_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

    def is_expired(self, timeout_seconds: float) -> bool:
        """Check if the action has exceeded its timeout."""
        return time.time() - self.created_at > timeout_seconds

    def to_dict(self) -> Dict[str, Any]:
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


# ─── Exceptions ───────────────────────────────────────────────────────


class GateError(Exception):
    """Raised when an action is blocked by the SovereignGate."""


class GateNotApproved(GateError):
    """Action has not been approved by the operator."""


class GateExpired(GateError):
    """Action approval window has expired."""


class GateInvalidSignature(GateError):
    """HMAC signature does not match."""


# ─── SovereignGate ────────────────────────────────────────────────────


_gate_instance: Optional[SovereignGate] = None


class SovereignGate:
    """
    L3 Action Interception Middleware.

    Every action classified as L3_EXECUTE or L4_MUTATE must pass
    through this gate. The gate generates an HMAC-SHA256 challenge
    that the operator must sign before execution proceeds.

    Modes:
      - ENFORCE:    Block execution until operator signs (production)
      - AUDIT_ONLY: Log the action but allow execution (development)
      - DISABLED:   Transparent passthrough (testing)
    """

    DEFAULT_TIMEOUT = 300  # 5 minutes

    def __init__(
        self,
        policy: Optional[GatePolicy] = None,
        secret: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        # Resolve policy from env if not provided
        if policy is None:
            env = os.environ.get("CORTEX_ENV", "dev").lower()
            policy = GatePolicy.ENFORCE if env == "prod" else GatePolicy.AUDIT_ONLY

        self.policy = policy
        self.timeout = timeout
        self._secret = (
            secret
            or os.environ.get("CORTEX_GATE_SECRET")
            or os.environ.get("CORTEX_VAULT_KEY")
            or "cortex-dev-secret"  # Fallback for dev only
        ).encode("utf-8")

        self._pending: Dict[str, PendingAction] = {}
        self._audit_log: List[Dict[str, Any]] = []

        logger.info(
            "SovereignGate initialized — policy=%s timeout=%ds",
            self.policy.value,
            int(self.timeout),
        )

    # ─── Core API ─────────────────────────────────────────────────

    def request_approval(
        self,
        level: ActionLevel,
        description: str,
        command: Optional[List[str]] = None,
        project: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> PendingAction:
        """
        Register an L3/L4 action and generate an HMAC challenge.

        Returns a PendingAction with the challenge. The operator
        must sign this challenge to approve execution.
        """
        action_id = str(uuid.uuid4())[:12]

        # Generate HMAC challenge
        payload = json.dumps(
            {
                "id": action_id,
                "level": level.value,
                "desc": description,
                "ts": time.time(),
            },
            sort_keys=True,
        )

        challenge = hmac.new(self._secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()

        action = PendingAction(
            action_id=action_id,
            level=level,
            description=description,
            command=command,
            project=project,
            context=context or {},
            hmac_challenge=challenge,
        )

        self._pending[action_id] = action
        self._log_audit("ACTION_REQUESTED", action)

        logger.info(
            "⚡ Gate: Action %s requested — %s [%s]",
            action_id,
            description,
            level.value,
        )

        return action

    def approve(
        self,
        action_id: str,
        signature: str,
        operator_id: str = "operator",
    ) -> bool:
        """
        Approve an action with HMAC signature verification.

        The signature must match the challenge generated during
        request_approval.
        """
        action = self._get_action(action_id)

        if action.is_expired(self.timeout):
            action.status = ActionStatus.EXPIRED
            self._log_audit("ACTION_EXPIRED", action)
            raise GateExpired(f"Action {action_id} expired after {self.timeout}s")

        # Verify HMAC signature
        if not hmac.compare_digest(signature, action.hmac_challenge):
            self._log_audit("INVALID_SIGNATURE", action)
            raise GateInvalidSignature(f"Invalid signature for action {action_id}")

        action.status = ActionStatus.APPROVED
        action.approved_at = time.time()
        action.operator_id = operator_id
        self._log_audit("ACTION_APPROVED", action)

        logger.info(
            "✅ Gate: Action %s approved by %s",
            action_id,
            operator_id,
        )
        return True

    def approve_interactive(self, action_id: str) -> bool:
        """
        Interactive CLI approval — prompts the operator directly.

        In AUDIT_ONLY mode, auto-approves with a log entry.
        In DISABLED mode, does nothing.
        """
        action = self._get_action(action_id)

        if self.policy == GatePolicy.DISABLED:
            action.status = ActionStatus.APPROVED
            return True

        if self.policy == GatePolicy.AUDIT_ONLY:
            logger.info(
                "🔍 AUDIT: Action %s would require approval — %s",
                action_id,
                action.description,
            )
            action.status = ActionStatus.APPROVED
            action.approved_at = time.time()
            action.operator_id = "auto-audit"
            self._log_audit("AUTO_APPROVED_AUDIT", action)
            return True

        # ENFORCE mode — actual interactive prompt
        print(f"\n{'=' * 60}")
        print(f"⚡ SOVEREIGN GATE — L3 ACTION APPROVAL REQUIRED")
        print(f"{'=' * 60}")
        print(f"  Action:  {action.description}")
        print(f"  Level:   {action.level.value}")
        print(f"  Project: {action.project or 'N/A'}")
        if action.command:
            cmd_str = " ".join(action.command)
            if len(cmd_str) > 100:
                cmd_str = cmd_str[:100] + "..."
            print(f"  Command: {cmd_str}")
        print(f"  ID:      {action_id}")
        print(f"{'=' * 60}")

        try:
            response = input("  ¿Aprobar ejecución? [s/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            response = "n"

        if response in ("s", "y", "si", "yes"):
            action.status = ActionStatus.APPROVED
            action.approved_at = time.time()
            action.operator_id = "interactive"
            self._log_audit("ACTION_APPROVED_INTERACTIVE", action)
            logger.info("✅ Gate: Action %s approved interactively", action_id)
            return True
        else:
            action.status = ActionStatus.DENIED
            self._log_audit("ACTION_DENIED", action)
            logger.warning("❌ Gate: Action %s denied by operator", action_id)
            raise GateNotApproved(f"Action {action_id} denied by operator")

    def deny(self, action_id: str, reason: str = "") -> None:
        """Explicitly deny a pending action."""
        action = self._get_action(action_id)
        action.status = ActionStatus.DENIED
        action.context["deny_reason"] = reason
        self._log_audit("ACTION_DENIED", action)
        logger.warning("❌ Gate: Action %s denied — %s", action_id, reason)

    def execute_subprocess(
        self,
        action_id: str,
        cmd: List[str],
        **kwargs: Any,
    ) -> subprocess.CompletedProcess:
        """
        Execute a subprocess ONLY if the action is approved.

        This is the single choke-point for all L3 subprocess calls.
        """
        action = self._get_action(action_id)

        if action.status != ActionStatus.APPROVED:
            raise GateNotApproved(f"Action {action_id} is {action.status.value}, not approved")

        if action.is_expired(self.timeout):
            action.status = ActionStatus.EXPIRED
            self._log_audit("ACTION_EXPIRED_PRE_EXEC", action)
            raise GateExpired(f"Action {action_id} expired before execution")

        # Execute
        logger.info("🚀 Gate: Executing approved action %s", action_id)
        result = subprocess.run(cmd, **kwargs)
        action.status = ActionStatus.EXECUTED
        action.executed_at = time.time()
        action.result = {
            "returncode": result.returncode,
            "stdout_len": len(result.stdout or ""),
            "stderr_len": len(result.stderr or ""),
        }
        self._log_audit("ACTION_EXECUTED", action)
        return result

    # ─── Query API ────────────────────────────────────────────────

    def get_pending(self) -> List[PendingAction]:
        """Return all pending actions, expiring stale ones first."""
        self._sweep_expired()
        return [a for a in self._pending.values() if a.status == ActionStatus.PENDING]

    def get_audit_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return the most recent audit log entries."""
        return self._audit_log[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Return gate status summary."""
        self._sweep_expired()
        statuses = {}
        for a in self._pending.values():
            s = a.status.value
            statuses[s] = statuses.get(s, 0) + 1
        return {
            "policy": self.policy.value,
            "timeout_seconds": int(self.timeout),
            "pending": statuses.get("pending", 0),
            "approved": statuses.get("approved", 0),
            "denied": statuses.get("denied", 0),
            "expired": statuses.get("expired", 0),
            "executed": statuses.get("executed", 0),
            "total_audit_entries": len(self._audit_log),
        }

    # ─── Internal ─────────────────────────────────────────────────

    def _get_action(self, action_id: str) -> PendingAction:
        """Retrieve an action by ID or raise."""
        action = self._pending.get(action_id)
        if action is None:
            raise GateError(f"Unknown action ID: {action_id}")
        return action

    def _sweep_expired(self) -> int:
        """Mark expired pending actions. Returns count of expired."""
        count = 0
        for action in self._pending.values():
            if action.status == ActionStatus.PENDING and action.is_expired(self.timeout):
                action.status = ActionStatus.EXPIRED
                self._log_audit("ACTION_AUTO_EXPIRED", action)
                count += 1
        return count

    def _log_audit(self, event: str, action: PendingAction) -> None:
        """Append to the in-memory audit log."""
        entry = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **action.to_dict(),
        }
        self._audit_log.append(entry)


# ─── Singleton Access ─────────────────────────────────────────────────


def get_gate(
    policy: Optional[GatePolicy] = None,
    secret: Optional[str] = None,
    timeout: float = SovereignGate.DEFAULT_TIMEOUT,
) -> SovereignGate:
    """Get or create the global SovereignGate singleton."""
    global _gate_instance
    if _gate_instance is None:
        _gate_instance = SovereignGate(
            policy=policy,
            secret=secret,
            timeout=timeout,
        )
    return _gate_instance


def reset_gate() -> None:
    """Reset the global gate (for testing)."""
    global _gate_instance
    _gate_instance = None
