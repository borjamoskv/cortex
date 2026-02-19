"""CORTEX v4.3 — Thought Orchestra Module.

Orquestación multi-modelo con fusión por consenso.
N modelos piensan en paralelo, sus respuestas se fusionan
para producir una respuesta superior a cualquier modelo individual.
"""

from cortex.thinking.orchestra import ThoughtOrchestra
from cortex.thinking.fusion import ThoughtFusion

__all__ = ["ThoughtOrchestra", "ThoughtFusion"]
