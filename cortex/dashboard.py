"""
CORTEX v4.0 — Embedded Dashboard.

Serves a premium, "Industrial Noir" dashboard UI at /dashboard.
Loads HTML from templates/dashboard.html — zero frontend build step.
"""

from __future__ import annotations

from pathlib import Path

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_DASHBOARD_CACHE: str | None = None


def get_dashboard_html() -> str:
    """Return the dashboard HTML, loaded from template and cached."""
    global _DASHBOARD_CACHE  # noqa: PLW0603
    if _DASHBOARD_CACHE is None:
        template_path = _TEMPLATE_DIR / "dashboard.html"
        _DASHBOARD_CACHE = template_path.read_text(encoding="utf-8")
    return _DASHBOARD_CACHE
