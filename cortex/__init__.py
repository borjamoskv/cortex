"""
CORTEX — The Sovereign Ledger for AI Agents.

Local-first memory infrastructure with vector search, temporal facts,
and cryptographic vaults. Zero network dependencies.
"""

import sys

try:
    # Use pysqlite3 if available (allows newer SQLite versions + extensions)
    __import__("pysqlite3")
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

__version__ = "4.0.0a1"
__author__ = "Borja Moskv"

from cortex.engine import CortexEngine

__all__ = ["CortexEngine", "__version__"]
