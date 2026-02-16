"""
CORTEX v4.0 — Core Engine Proxy.

This file provides backward compatibility for the monolithic engine.py
by importing from the new modular package.
"""

from cortex.engine.__init__ import CortexEngine, Fact

__all__ = ["CortexEngine", "Fact"]
