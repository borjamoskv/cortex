"""
CORTEX v4.0 — Custom Exceptions.

Typed error hierarchy to avoid leaking internal DB details
through API boundaries (Sprint 0 security directive).
"""


class CortexError(Exception):
    """Base exception for all CORTEX errors."""


class DatabaseTransactionError(CortexError):
    """Raised when a database transaction fails and has been rolled back.

    This exception sanitizes internal SQLite error details so they are
    never exposed to external callers or API consumers.
    """


class FactNotFound(CortexError):
    """Raised when a fact is not found."""


class ProjectNotFound(CortexError):
    """Raised when a project is not found."""


class ThreadPoolExhausted(CortexError):
    """Raised when thread pool is saturated."""
