"""CORTEX MCP Toolbox Bridge — External Database Connectivity.

Provides a bridge between CORTEX and Google's MCP Toolbox for Databases,
enabling agents to query external databases (PostgreSQL, AlloyDB, MySQL,
Spanner) through a secure, centralized control plane.

The Toolbox server runs as an external process. This module integrates
via the `toolbox-core` Python SDK.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger("cortex.mcp.toolbox_bridge")

_TOOLBOX_AVAILABLE = False
try:
    from toolbox_core import ToolboxClient  # type: ignore

    _TOOLBOX_AVAILABLE = True
except ImportError:
    ToolboxClient = None  # type: ignore
    logger.debug(
        "Toolbox SDK not installed. Install with: pip install toolbox-core"
    )


# ─── Configuration ────────────────────────────────────────────────────


@dataclass
class ToolboxConfig:
    """Configuration for connecting to an MCP Toolbox server."""

    server_url: str = "http://127.0.0.1:5000"
    toolset: str = ""
    timeout_seconds: float = 30.0
    allowed_server_urls: list[str] = field(
        default_factory=lambda: ["http://127.0.0.1:5000", "http://localhost:5000"]
    )

    @classmethod
    def from_env(cls) -> "ToolboxConfig":
        """Create config from environment variables."""
        return cls(
            server_url=os.environ.get("TOOLBOX_URL", "http://127.0.0.1:5000"),
            toolset=os.environ.get("TOOLBOX_TOOLSET", ""),
            timeout_seconds=float(os.environ.get("TOOLBOX_TIMEOUT", "30")),
        )


# ─── Bridge ───────────────────────────────────────────────────────────


class ToolboxBridge:
    """Bridge between CORTEX and an MCP Toolbox server.

    Connects to an external Toolbox server and loads database tools
    that can be used by CORTEX ADK agents.
    """

    def __init__(self, config: ToolboxConfig | None = None) -> None:
        self.config = config or ToolboxConfig.from_env()
        self._client: "ToolboxClient | None" = None
        self._tools: list = []

    @property
    def is_available(self) -> bool:
        """Check if Toolbox SDK is installed."""
        return _TOOLBOX_AVAILABLE

    def _validate_server_url(self) -> None:
        """Validate that the server URL is in the allowlist."""
        url = self.config.server_url.rstrip("/")
        allowed = [u.rstrip("/") for u in self.config.allowed_server_urls]
        if url not in allowed:
            raise ValueError(
                f"Toolbox server URL '{url}' is not in the allowlist. "
                f"Allowed: {allowed}"
            )

    async def connect(self) -> bool:
        """Connect to the Toolbox server and load tools.

        Returns:
            True if connection succeeded, False otherwise.
        """
        if not _TOOLBOX_AVAILABLE:
            logger.error("Toolbox SDK not installed")
            return False

        self._validate_server_url()

        try:
            self._client = ToolboxClient(self.config.server_url)

            if self.config.toolset:
                self._tools = await self._client.load_toolset(self.config.toolset)
            else:
                self._tools = await self._client.load_toolset()

            logger.info(
                "Connected to Toolbox at %s — loaded %d tools",
                self.config.server_url,
                len(self._tools),
            )
            return True
        except (ConnectionError, OSError, RuntimeError) as exc:
            logger.error("Failed to connect to Toolbox: %s", exc)
            self._client = None
            self._tools = []
            return False

    @property
    def tools(self) -> list:
        """Get loaded Toolbox tools (for use with ADK agents)."""
        return list(self._tools)

    @property
    def tool_names(self) -> list[str]:
        """Get names of loaded Toolbox tools."""
        return [getattr(t, "name", str(t)) for t in self._tools]

    async def close(self) -> None:
        """Close the Toolbox connection."""
        if self._client:
            try:
                await self._client.close()
            except (ConnectionError, OSError):
                pass
        self._client = None
        self._tools = []

    def __repr__(self) -> str:
        status = "connected" if self._client else "disconnected"
        return (
            f"ToolboxBridge(url={self.config.server_url!r}, "
            f"status={status}, tools={len(self._tools)})"
        )


# ─── Factory ──────────────────────────────────────────────────────────


async def create_toolbox_bridge(
    server_url: str | None = None,
    toolset: str = "",
) -> ToolboxBridge:
    """Create and connect a ToolboxBridge.

    Args:
        server_url: Toolbox server URL (default: from env).
        toolset: Named toolset to load (default: all tools).

    Returns:
        Connected ToolboxBridge instance.
    """
    config = ToolboxConfig.from_env()
    if server_url:
        config.server_url = server_url
        # Auto-add to allowlist if explicitly provided
        if server_url not in config.allowed_server_urls:
            config.allowed_server_urls.append(server_url)
    if toolset:
        config.toolset = toolset

    bridge = ToolboxBridge(config)
    await bridge.connect()
    return bridge
