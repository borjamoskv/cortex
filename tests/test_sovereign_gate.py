"""
CORTEX v4.0 — SovereignGate Tests.

Tests for L3 action interception, HMAC approval, expiry, and policy modes.
"""

import time

import pytest

from cortex.sovereign_gate import (
    ActionLevel,
    ActionStatus,
    GatePolicy,
    GateError,
    GateExpired,
    GateInvalidSignature,
    GateNotApproved,
    SovereignGate,
    reset_gate,
)


@pytest.fixture(autouse=True)
def clean_gate():
    """Reset global gate singleton between tests."""
    reset_gate()
    yield
    reset_gate()


@pytest.fixture
def gate():
    """Create a gate in ENFORCE mode with a known secret."""
    return SovereignGate(
        policy=GatePolicy.ENFORCE,
        secret="test-secret-key",
        timeout=10,
    )


@pytest.fixture
def audit_gate():
    """Create a gate in AUDIT_ONLY mode."""
    return SovereignGate(
        policy=GatePolicy.AUDIT_ONLY,
        secret="test-secret-key",
        timeout=10,
    )


@pytest.fixture
def disabled_gate():
    """Create a gate in DISABLED mode."""
    return SovereignGate(
        policy=GatePolicy.DISABLED,
        secret="test-secret-key",
        timeout=10,
    )


class TestActionRequest:
    """Test action request and challenge generation."""

    def test_request_creates_pending_action(self, gate):
        action = gate.request_approval(
            level=ActionLevel.L3_EXECUTE,
            description="Test mission launch",
        )
        assert action.status == ActionStatus.PENDING
        assert action.level == ActionLevel.L3_EXECUTE
        assert action.hmac_challenge != ""
        assert len(action.action_id) == 12

    def test_request_with_full_context(self, gate):
        action = gate.request_approval(
            level=ActionLevel.L3_EXECUTE,
            description="Deploy to prod",
            command=["node", "swarm.js", "--mission", "audit"],
            project="cortex",
            context={"formation": "IRON_DOME", "agents": 10},
        )
        assert action.command == ["node", "swarm.js", "--mission", "audit"]
        assert action.project == "cortex"
        assert action.context["agents"] == 10

    def test_multiple_actions_get_unique_ids(self, gate):
        a1 = gate.request_approval(ActionLevel.L3_EXECUTE, "A")
        a2 = gate.request_approval(ActionLevel.L3_EXECUTE, "B")
        assert a1.action_id != a2.action_id
        assert a1.hmac_challenge != a2.hmac_challenge


class TestApproval:
    """Test HMAC signature approval."""

    def test_approve_with_valid_signature(self, gate):
        action = gate.request_approval(ActionLevel.L3_EXECUTE, "Test")
        result = gate.approve(
            action.action_id,
            signature=action.hmac_challenge,
            operator_id="borja",
        )
        assert result is True
        assert action.status == ActionStatus.APPROVED
        assert action.operator_id == "borja"
        assert action.approved_at is not None

    def test_reject_invalid_signature(self, gate):
        action = gate.request_approval(ActionLevel.L3_EXECUTE, "Test")
        with pytest.raises(GateInvalidSignature):
            gate.approve(action.action_id, signature="wrong-sig")

    def test_reject_unknown_action_id(self, gate):
        with pytest.raises(GateError, match="Unknown action ID"):
            gate.approve("nonexistent-id", signature="anything")


class TestExpiry:
    """Test action expiration."""

    def test_expired_action_cannot_be_approved(self, gate):
        # Create gate with very short timeout
        short_gate = SovereignGate(
            policy=GatePolicy.ENFORCE,
            secret="test-secret",
            timeout=0.01,  # 10ms
        )
        action = short_gate.request_approval(ActionLevel.L3_EXECUTE, "Test")
        time.sleep(0.05)
        with pytest.raises(GateExpired):
            short_gate.approve(action.action_id, action.hmac_challenge)

    def test_sweep_marks_expired_actions(self, gate):
        short_gate = SovereignGate(
            policy=GatePolicy.ENFORCE,
            secret="test-secret",
            timeout=0.01,
        )
        short_gate.request_approval(ActionLevel.L3_EXECUTE, "A")
        short_gate.request_approval(ActionLevel.L3_EXECUTE, "B")
        time.sleep(0.05)
        count = short_gate._sweep_expired()
        assert count == 2


class TestExecution:
    """Test subprocess execution gate."""

    def test_execute_approved_action(self, gate):
        action = gate.request_approval(
            ActionLevel.L3_EXECUTE,
            "Run echo",
            command=["echo", "hello"],
        )
        gate.approve(action.action_id, action.hmac_challenge, "operator")
        result = gate.execute_subprocess(
            action.action_id,
            ["echo", "sovereign gate works"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "sovereign gate works" in result.stdout
        assert action.status == ActionStatus.EXECUTED

    def test_block_unapproved_execution(self, gate):
        action = gate.request_approval(ActionLevel.L3_EXECUTE, "Test")
        with pytest.raises(GateNotApproved):
            gate.execute_subprocess(action.action_id, ["echo", "blocked"])

    def test_block_denied_execution(self, gate):
        action = gate.request_approval(ActionLevel.L3_EXECUTE, "Test")
        gate.deny(action.action_id, reason="Too risky")
        with pytest.raises(GateNotApproved):
            gate.execute_subprocess(action.action_id, ["echo", "denied"])


class TestDeny:
    """Test action denial."""

    def test_deny_action(self, gate):
        action = gate.request_approval(ActionLevel.L3_EXECUTE, "Dangerous")
        gate.deny(action.action_id, reason="Not authorized")
        assert action.status == ActionStatus.DENIED
        assert action.context["deny_reason"] == "Not authorized"


class TestAuditOnly:
    """Test AUDIT_ONLY policy — logs but doesn't block."""

    def test_audit_mode_auto_approves(self, audit_gate):
        action = audit_gate.request_approval(ActionLevel.L3_EXECUTE, "Test")
        audit_gate.approve_interactive(action.action_id)
        assert action.status == ActionStatus.APPROVED
        assert action.operator_id == "auto-audit"

    def test_audit_mode_logs_event(self, audit_gate):
        action = audit_gate.request_approval(ActionLevel.L3_EXECUTE, "Test")
        audit_gate.approve_interactive(action.action_id)
        log = audit_gate.get_audit_log()
        events = [e["event"] for e in log]
        assert "AUTO_APPROVED_AUDIT" in events


class TestDisabled:
    """Test DISABLED policy — transparent passthrough."""

    def test_disabled_mode_auto_approves(self, disabled_gate):
        action = disabled_gate.request_approval(ActionLevel.L3_EXECUTE, "Test")
        disabled_gate.approve_interactive(action.action_id)
        assert action.status == ActionStatus.APPROVED


class TestAuditLog:
    """Test the audit trail."""

    def test_audit_log_records_events(self, gate):
        action = gate.request_approval(ActionLevel.L3_EXECUTE, "Test")
        gate.approve(action.action_id, action.hmac_challenge, "op")
        gate.execute_subprocess(
            action.action_id,
            ["echo", "ok"],
            capture_output=True,
            text=True,
        )
        log = gate.get_audit_log()
        events = [e["event"] for e in log]
        assert "ACTION_REQUESTED" in events
        assert "ACTION_APPROVED" in events
        assert "ACTION_EXECUTED" in events

    def test_audit_log_respects_limit(self, gate):
        for i in range(10):
            gate.request_approval(ActionLevel.L3_EXECUTE, f"Action {i}")
        log = gate.get_audit_log(limit=5)
        assert len(log) == 5


class TestGateStatus:
    """Test status reporting."""

    def test_status_reports_policy(self, gate):
        status = gate.get_status()
        assert status["policy"] == "enforce"
        assert status["timeout_seconds"] == 10

    def test_status_counts_actions(self, gate):
        gate.request_approval(ActionLevel.L3_EXECUTE, "A")
        gate.request_approval(ActionLevel.L3_EXECUTE, "B")
        action = gate.request_approval(ActionLevel.L3_EXECUTE, "C")
        gate.deny(action.action_id)
        status = gate.get_status()
        assert status["pending"] == 2
        assert status["denied"] == 1


class TestSerialization:
    """Test to_dict for API responses."""

    def test_to_dict_format(self, gate):
        action = gate.request_approval(
            ActionLevel.L3_EXECUTE,
            "Test serialization",
            command=["node", "swarm.js"],
            project="cortex",
        )
        d = action.to_dict()
        assert d["action_id"] == action.action_id
        assert d["level"] == "L3_EXECUTE"
        assert d["status"] == "pending"
        assert "created_at" in d
        assert d["command"] == ["node", "swarm.js"]
