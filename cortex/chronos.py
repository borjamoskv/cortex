"""
CHRONOS-1 The Senior Benchmark

Implements the mathematical logic to estimate Human Senior Time (HST)
versus an AI agent completion time. Formula:
HST = T_c (Context) + T_d (Design) + T_i (Implementation) + T_b (Debugging) + T_p (Penalty)
"""

import random
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class ChronosMetrics:
    ai_time_secs: float
    human_time_secs: float
    asymmetry_factor: float
    context_msg: str
    tip: str
    anti_tip: str


class ChronosEngine:
    """Core mathematical engine for CHRONOS-1."""

    COMPLEXITY_MULTIPLIERS: Dict[str, Dict[str, float]] = {
        "low": {
            "t_c": 1.5,  # 1.5x AI time for context loading
            "t_d": 1.0,  # 1.0x AI time for design
            "t_i": 2.0,  # 2.0x AI time for typing
            "t_b": 0.5,  # 0.5x AI time for debugging
            "t_p": 0.0,  # No penalty
            "context": "Un humano habría localizado el archivo, añadido el código básico y probado el output. Tarea procedimental."
        },
        "medium": {
            "t_c": 3.0,
            "t_d": 2.0,
            "t_i": 3.0,
            "t_b": 2.0,
            "t_p": 1.0,
            "context": "Un Senior habría tardado en entender el alcance, lidiar con typings/linting y arreglar un par de bugs sutiles antes del commit."
        },
        "high": {
            "t_c": 5.0,
            "t_d": 5.0,
            "t_i": 4.0,
            "t_b": 8.0,
            "t_p": 3.0,
            "context": "Arquitectura pesada. El humano habría leído documentación, diseñado el estado global y refactorizado a media ejecución."
        },
        "god": {
            "t_c": 10.0,
            "t_d": 15.0,
            "t_i": 5.0,
            "t_b": 15.0,
            "t_p": 5.0,
            "context": "Orquestación sistémica (Swarm/OS). Un humano habría requerido validación adversaria intensiva y debugging existencial profundo."
        }
    }

    TIPS_POOL: Dict[str, List[str]] = {
        "low": [
            "Para tareas triviales, asegúrate de mantener el 'Context Loading' limpio con buenos READMEs.",
            "Automatiza este tipo de tareas con scripts triviales en lugar de invocaciones complejas LLM.",
            "Usa snippets de código en VS Code para acortar aún más tu Typing (T_i)."
        ],
        "medium": [
            "El Debugging (T_b) humano es costoso. Invierte tiempo bloqueando tipos en Python con Mypy.",
            "El Context Switching te castiga (T_p). Intenta agrupar las tareas relacionales en un sprint de enfoque.",
            "El diseño previo reduce el tiempo de implementación. Usa EVOLV-1 antes para afinar la intención."
        ],
        "high": [
            "En arquitectura pesada, el diseño (T_d) es crucial. Dibuja un diagrama Mermaid antes de codificar.",
            "La asimetría aquí es brutal. Delega siempre el boilerplate a MOSKV-1 y dedícate al refinamiento estratégico.",
            "Prueba mutacional: rompe tu código intencionadamente para ver si los test fallan. El Senior humano lo haría."
        ],
        "god": [
            "La orquestación sistémica requiere 'War Council' adversarial. Nunca vayas a ciegas a producción.",
            "Documenta en CORTEX el porqué de esta decisión God-Mode. En 6 meses no recordarás el contexto.",
            "Mantén el 'Zero Concepto' - si puedes simularlo antes de aplicarlo en el ecosistema, hazlo."
        ]
    }

    ANTI_TIPS_POOL: Dict[str, List[str]] = {
        "low": [
            "Crear una abstracción sobre-ingenierizada para un problema de 3 líneas.",
            "Aplicar arquitecturas God-Mode (Clean Architecture, CQRS) donde bastaba un script secuencial.",
            "Ignorar herramientas nativas (grep, awk) intentando escribir el código enteramente en Python/JS."
        ],
        "medium": [
            "Escribir el código por completo del tirón sin tests intermedios ni type-checking.",
            "Usar variables globales o estado mutable compartido por 'ahorrar tiempo'.",
            "Copiar y pegar de un proyecto anterior sin adaptar el contexto."
        ],
        "high": [
            "Empezar a programar sin diseñar ni escribir especificaciones arquitectónicas (SKILL.md).",
            "Ignorar el desacoplamiento: mezclar interfaz gráfica con llamadas directas a base de datos.",
            "Asumir que 'el caso feliz siempre ocurre' ignorando errores de red, permisos o asincronía."
        ],
        "god": [
            "Escribir código altamente acoplado que rompe el enjambre si un agente falla (No Byzantine Fault Tolerance).",
            "Construir sin persistencia. La amnesia en orquestadores complejos es la muerte sistémica.",
            "Saturar el modelo con prompts excesivamente largos sin comprimir primero en un Blackboard pattern."
        ]
    }

    @classmethod
    def analyze(cls, ai_time_secs: float, complexity: str = "medium") -> ChronosMetrics:
        """
        Calculates the Human Senior Time (HST) based on AI completion time and complexity class.
        Returns the full metrics dataclass.
        """
        complexity = complexity.lower()
        if complexity not in cls.COMPLEXITY_MULTIPLIERS:
            raise ValueError(f"Unknown complexity '{complexity}'. Must be one of: {list(cls.COMPLEXITY_MULTIPLIERS.keys())}")

        multipliers = cls.COMPLEXITY_MULTIPLIERS[complexity]
        
        # Base multipliers
        t_c = ai_time_secs * multipliers["t_c"]
        t_d = ai_time_secs * multipliers["t_d"]
        t_i = ai_time_secs * multipliers["t_i"]
        t_b = ai_time_secs * multipliers["t_b"]
        t_p = ai_time_secs * multipliers["t_p"]

        hst = t_c + t_d + t_i + t_b + t_p
        
        # Baselines
        baseline_mins_human = {
            "low": 3 * 60,
            "medium": 15 * 60,
            "high": 60 * 60,
            "god": 180 * 60
        }
        
        # Take the maximum between math and human baseline reality
        hst = max(hst, baseline_mins_human[complexity])
        
        asym = hst / ai_time_secs if ai_time_secs > 0 else 0

        # Select a random appropriate tip and anti-tip
        tip = random.choice(cls.TIPS_POOL[complexity])
        anti_tip = random.choice(cls.ANTI_TIPS_POOL[complexity])

        return ChronosMetrics(
            ai_time_secs=ai_time_secs,
            human_time_secs=hst,
            asymmetry_factor=round(asym, 1),
            context_msg=multipliers["context"],
            tip=tip,
            anti_tip=anti_tip
        )

    @staticmethod
    def format_time(seconds: float) -> str:
        """Formats seconds into readable human time (minutes, hours, days)."""
        if seconds < 60:
            return f"{int(seconds)} segundos"
        minutes = seconds / 60
        if minutes < 60:
            return f"{int(minutes)} minutos" if int(minutes) > 1 else "1 minuto"
        
        hours = minutes / 60
        if hours < 8:
            return f"{round(hours, 1)} hrs" if round(hours, 1) != 1.0 else "1 hr"
            
        days = hours / 8  # 8 hour workday
        return f"{round(days, 1)} días" if round(days, 1) != 1.0 else "1 día"
