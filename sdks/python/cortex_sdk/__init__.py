"""
CORTEX SDK — Thin Python client for the CORTEX Memory API.

Usage:
    from cortex_sdk import Cortex

    ctx = Cortex("http://localhost:8000", api_key="your-key")
    ctx.store("user prefers dark mode", project="myapp")
    results = ctx.search("preferences")
    ok = ctx.verify()
"""

from cortex_sdk.client import Cortex

__all__ = ["Cortex"]
__version__ = "0.1.0"
