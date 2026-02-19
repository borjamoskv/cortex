"""CORTEX v4.3 — Thought Orchestra Module.

Orquestación multi-modelo con fusión por consenso.
N modelos piensan en paralelo, sus respuestas se fusionan
para producir una respuesta superior a cualquier modelo individual.
"""

from cortex.thinking.orchestra import (
    ThoughtOrchestra,
    OrchestraConfig,
    ThinkingMode,
    ThinkingRecord,
)
from cortex.thinking.fusion import (
    ThoughtFusion,
    FusionStrategy,
    FusedThought,
    ModelResponse,
)

__all__ = [
    "ThoughtOrchestra",
    "OrchestraConfig",
    "ThinkingMode",
    "ThinkingRecord",
    "ThoughtFusion",
    "FusionStrategy",
    "FusedThought",
    "ModelResponse",
]

