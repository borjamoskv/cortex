"""
CORTEX v4.0 — SovereignGate Exceptions.
"""


class GateError(Exception):
    """Raised when an action is blocked by the SovereignGate."""


class GateNotApproved(GateError):
    """Action has not been approved by the operator."""


class GateExpired(GateError):
    """Action approval window has expired."""


class GateInvalidSignature(GateError):
    """HMAC signature does not match."""
