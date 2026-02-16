"""Tests for CORTEX MCP Server (basic structure tests, no mcp SDK required)."""

import pytest


class TestMCPServerModule:
    """Test the MCP server module can be imported and configured."""

    def test_module_import(self):
        """MCP server module should be importable."""
        from cortex.mcp import server as mcp_server
        assert hasattr(mcp_server, "create_mcp_server")
        assert hasattr(mcp_server, "run_server")

    def test_mcp_availability_flag(self):
        """Should detect whether MCP SDK is available."""
        from cortex.mcp.server import _MCP_AVAILABLE
        # Just verify the flag is a bool (value depends on installation)
        assert isinstance(_MCP_AVAILABLE, bool)

    def test_create_server_without_mcp_raises(self):
        """If MCP SDK is not installed, create_mcp_server should raise ImportError."""
        from cortex.mcp.server import _MCP_AVAILABLE
        if not _MCP_AVAILABLE:
            with pytest.raises(ImportError, match="MCP SDK not installed"):
                from cortex.mcp.server import create_mcp_server
                create_mcp_server()
        else:
            pytest.skip("MCP SDK is installed, cannot test ImportError path")
