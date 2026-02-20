"""
CORTEX v4.0 — Internationalization Module (i18n).

Provides multilingual support for the API layer.
Default: English (en)
Supported: Spanish (es), Basque (eu)
"""


from functools import lru_cache

__all__ = [
    "get_trans",
    "get_supported_languages",
    "DEFAULT_LANGUAGE",
    "SUPPORTED_LANGUAGES",
]

# Defaults and supported languages
DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = frozenset({"en", "es", "eu"})


def get_supported_languages() -> frozenset[str]:
    """Returns the set of languages officially supported by CORTEX."""
    return SUPPORTED_LANGUAGES


# Dictionary of translations
TRANSLATIONS: dict[str, dict[str, str]] = {
    # System Status
    "system_operational": {
        "en": "operational",
        "es": "operativo",
        "eu": "martxan",
    },
    "system_healthy": {
        "en": "healthy",
        "es": "saludable",
        "eu": "osasuntsu",
    },
    "engine_online": {
        "en": "online",
        "es": "en línea",
        "eu": "konektatuta",
    },

    # Errors
    "error_too_many_requests": {
        "en": "Too Many Requests. Please slow down.",
        "es": "Demasiadas solicitudes. Por favor, reduce la velocidad.",
        "eu": "Eskaera gehiegi. Mesedez, moteldu.",
    },
    "error_internal_db": {
        "en": "Internal database error",
        "es": "Error interno de base de datos",
        "eu": "Datu-basearen barne errorea",
    },
    "error_unexpected": {
        "en": "An unexpected server error occurred.",
        "es": "Ha ocurrido un error inesperado del servidor.",
        "eu": "Zerbitzariaren ezusteko errorea gertatu da.",
    },
    "error_unauthorized": {
        "en": "Unauthorized access",
        "es": "Acceso no autorizado",
        "eu": "Baimenik gabeko sarbidea",
    },
    "error_not_found": {
        "en": "Resource not found",
        "es": "Recurso no encontrado",
        "eu": "Baliabidea ez da aurkitu",
    },
    "error_invalid_input": {
        "en": "Invalid input provided",
        "es": "Entrada no válida",
        "eu": "Sarrera baliogabea",
    },

    # Greetings / Info
    "info_service_desc": {
        "en": "Local-first memory infrastructure for AI agents.",
        "es": "Infraestructura de memoria local-first para agentes de IA.",
        "eu": "IA agenteentzako tokiko memoria azpiegitura.",
    },

    # Auth Errors
    "error_missing_auth": {
        "en": "Missing Authorization header",
        "es": "Falta la cabecera de autorización",
        "eu": "Baimen goiburua falta da",
    },
    "error_invalid_key_format": {
        "en": "Invalid key format. Use: Bearer <api-key>",
        "es": "Formato de clave no válido. Usa: Bearer <api-key>",
        "eu": "Gako formatu baliogabea. Erabili: Bearer <api-key>",
    },
    "error_invalid_revoked_key": {
        "en": "Invalid or revoked key",
        "es": "Clave no válida o revocada",
        "eu": "Gako baliogabea edo ezeztatua",
    },
    "error_missing_permission": {
        "en": "Missing permission: {permission}",
        "es": "Falta permiso: {permission}",
        "eu": "Baimen hau falta da: {permission}",
    },

    # Fact Errors
    "error_fact_not_found": {
        "en": "Fact #{id} not found",
        "es": "No se encontró el hecho #{id}",
        "eu": "Ez da aurkitu #{id} gertaera",
    },
    "error_namespace_mismatch": {
        "en": "Forbidden: Namespace mismatch",
        "es": "Prohibido: Conflicto de espacio de nombres",
        "eu": "Debekatua: Izen-espazio gatazka",
    },
    "error_forbidden": {
        "en": "Forbidden",
        "es": "Prohibido",
        "eu": "Debekatua",
    },

    # Admin / Path Validation
    "error_json_only": {
        "en": "Only JSON format supported via API",
        "es": "Solo se admite el formato JSON mediante la API",
        "eu": "JSON formatua bakarrik onartzen da API bidez",
    },
    "error_invalid_path_chars": {
        "en": "Invalid characters in path",
        "es": "Caracteres no válidos en la ruta",
        "eu": "Baliogabeko karaktereak bidean",
    },
    "error_path_workspace": {
        "en": "Path must be relative and within the workspace",
        "es": "La ruta debe ser relativa y dentro del espacio de trabajo",
        "eu": "Bideak erlatiboa izan behar du eta lan-eremuaren barruan",
    },
    "error_export_failed": {
        "en": "Export failed",
        "es": "Exportación fallida",
        "eu": "Esportazioak huts egin du",
    },
    "error_status_unavailable": {
        "en": "Status unavailable",
        "es": "Estado no disponible",
        "eu": "Egoera ez dago erabilgarri",
    },
    "error_auth_required": {
        "en": "Auth required",
        "es": "Se requiere autenticación",
        "eu": "Autentifikazioa beharrezkoa da",
    },
    # Daemon
    "error_daemon_no_data": {
        "en": "No data collected by daemons in last hour",
        "es": "No hay datos recogidos por los demonios en la última hora",
        "eu": "Deabruek ez dute daturik bildu azken orduan",
    },

    # Ledger
    "error_integrity_check_failed": {
        "en": "Integrity check failed: {detail}",
        "es": "Verificación de integridad fallida: {detail}",
        "eu": "Osotasun egiaztapenak huts egin du: {detail}",
    },
    "error_checkpoint_failed": {
        "en": "Checkpoint failed: {detail}",
        "es": "Checkpoint fallido: {detail}",
        "eu": "Checkpoint-ak huts egin du: {detail}",
    },

    # Graph
    "error_graph_forbidden": {
        "en": "Forbidden: Access to this project is denied",
        "es": "Prohibido: Acceso denegado a este proyecto",
        "eu": "Debekatua: Proiektu honetarako sarbidea ukatuta",
    },
    "error_graph_unavailable": {
        "en": "Graph unavailable",
        "es": "Grafo no disponible",
        "eu": "Grafoa ez dago erabilgarri",
    },

    # Agents
    "error_agent_registration_failed": {
        "en": "Failed to retrieve registered agent",
        "es": "Error al recuperar el agente registrado",
        "eu": "Erregistratutako agentea berreskuratzeak huts egin du",
    },
    "error_agent_internal": {
        "en": "Internal registration error",
        "es": "Error interno de registro",
        "eu": "Erregistroaren barne errorea",
    },
    "error_agent_not_found": {
        "en": "Agent not found",
        "es": "Agente no encontrado",
        "eu": "Agentea ez da aurkitu",
    },

    # Timing
    "error_heartbeat_failed": {
        "en": "Heartbeat failed",
        "es": "Latido fallido",
        "eu": "Bihotz-taupadak huts egin du",
    },
    "error_time_summary_failed": {
        "en": "Time summary failed",
        "es": "Resumen de tiempo fallido",
        "eu": "Denbora laburpenak huts egin du",
    },
    "error_time_report_failed": {
        "en": "Time report failed",
        "es": "Informe de tiempo fallido",
        "eu": "Denbora txostenak huts egin du",
    },
    "error_time_history_failed": {
        "en": "Time history failed",
        "es": "Historial de tiempo fallido",
        "eu": "Denbora historiak huts egin du",
    },
    "error_timing_forbidden": {
        "en": "Forbidden: Project mismatch",
        "es": "Prohibido: Proyecto no coincide",
        "eu": "Debekatua: Proiektua ez dator bat",
    },

    # Facts (remaining hardcoded)
    "error_internal_server": {
        "en": "Internal server error",
        "es": "Error interno del servidor",
        "eu": "Zerbitzariaren barne errorea",
    },
    "error_internal_voting": {
        "en": "Internal voting error",
        "es": "Error interno de votación",
        "eu": "Botaketaren barne errorea",
    },
    "error_deprecation_failed": {
        "en": "Deprecation failed",
        "es": "Deprecación fallida",
        "eu": "Zaharkitzeak huts egin du",
    },
}


@lru_cache(maxsize=1024)
def get_trans(key: str, lang: str | None = "en") -> str:
    """Retrieve a translation for a given key and language.
    
    Falls back to English if the language or key is missing.
    Cached for high-performance localized responses (Sovereign Level).
    """
    if not lang or not isinstance(lang, str):
        lang = "en"
        
    # Normalize lang code (e.g. 'es-ES' -> 'es')
    lang_code = lang.split("-")[0].lower()

    entry = TRANSLATIONS.get(key)
    if not entry:
        return key  # Return key if not found

    return entry.get(lang_code, entry.get("en", key))

