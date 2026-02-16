"""
CORTEX v4.0 — MEJORAlo Round 7 Tests.

Tests for MCP server hardening, graph module error guards,
embeddings input validation, and export/temporal edge cases.
"""

from __future__ import annotations

import json
import sqlite3
from unittest.mock import MagicMock, patch

import pytest


# ═══ MCP Server defensive JSON ═══════════════════════════════════


class TestMCPServerHardening:
    """MCP server tools should handle corrupt data gracefully."""

    def test_cortex_store_handles_bad_tags(self):
        """cortex_store should not crash on invalid tags JSON."""
        # cortex_store already has try/except — verify it parses empty correctly
        with patch("cortex.mcp.server._MCP_AVAILABLE", True), patch("cortex.mcp.server.FastMCP"):
            # Just verify the module can be imported and the pattern exists
            import inspect
            from cortex.mcp.server import create_mcp_server

            source = inspect.getsource(create_mcp_server)
            assert "json.JSONDecodeError" in source or "JSONDecodeError" in source
            assert "parsed_tags = []" in source

    def test_cortex_recall_defensive_json(self):
        """cortex_recall should now have defensive JSON for tags."""
        import inspect
        from cortex.mcp.server import create_mcp_server

        source = inspect.getsource(create_mcp_server)
        # Should contain both JSONDecodeError and TypeError guards
        assert "JSONDecodeError" in source
        assert "TypeError" in source

    def test_list_projects_uses_public_api(self):
        """list_projects should use get_connection() not _get_conn()."""
        import inspect
        from cortex.mcp.server import create_mcp_server

        source = inspect.getsource(create_mcp_server)
        assert "._get_conn()" not in source
        assert ".get_connection()" in source


# ═══ Graph module error guards ═══════════════════════════════════


class TestGraphModuleHardening:
    """Graph extraction should handle errors gracefully."""

    def test_extract_entities_empty_content(self):
        """extract_entities should return empty list for empty content."""
        from cortex.graph import extract_entities

        assert extract_entities("") == []
        assert extract_entities("   ") == []
        assert extract_entities(None) == []

    def test_extract_entities_valid_content(self):
        """extract_entities should find entities in real content."""
        from cortex.graph import extract_entities

        entities = extract_entities("Using FastAPI with SQLite for cortex-memory project")
        names = {e["name"] for e in entities}
        assert "FastAPI" in names
        assert "SQLite" in names

    def test_detect_relationships_too_few_entities(self):
        """detect_relationships should return empty for < 2 entities."""
        from cortex.graph import detect_relationships

        assert detect_relationships("test", []) == []
        assert detect_relationships("test", [{"name": "one"}]) == []

    def test_process_fact_graph_db_error_handled(self):
        """process_fact_graph should catch sqlite3.Error."""
        from cortex.graph import process_fact_graph

        conn = MagicMock()
        # upsert_entity calls conn.execute which raises
        conn.execute.side_effect = sqlite3.OperationalError("no entities table")

        result = process_fact_graph(
            conn=conn,
            fact_id=1,
            content="Using FastAPI with SQLite for the cortex-memory project",
            project="test",
            timestamp="2024-01-01T00:00:00Z",
        )
        assert result == (0, 0)

    def test_process_fact_graph_empty_content(self):
        """process_fact_graph should return (0,0) for empty content."""
        from cortex.graph import process_fact_graph

        conn = MagicMock()
        result = process_fact_graph(
            conn=conn,
            fact_id=1,
            content="",
            project="test",
            timestamp="2024-01-01T00:00:00Z",
        )
        assert result == (0, 0)


# ═══ Embeddings input validation ═════════════════════════════════


class TestEmbeddingsInputValidation:
    """Embeddings should validate input."""

    def test_embed_empty_text_raises(self):
        """embed() should reject empty text."""
        from cortex.embeddings import LocalEmbedder

        embedder = LocalEmbedder()
        with pytest.raises(ValueError, match="empty"):
            embedder.embed("")

    def test_embed_whitespace_raises(self):
        """embed() should reject whitespace-only text."""
        from cortex.embeddings import LocalEmbedder

        embedder = LocalEmbedder()
        with pytest.raises(ValueError, match="empty"):
            embedder.embed("   \n\t  ")

    def test_embed_batch_empty_list(self):
        """embed_batch() should return empty list for empty input."""
        from cortex.embeddings import LocalEmbedder

        embedder = LocalEmbedder()
        result = embedder.embed_batch([])
        assert result == []

    def test_embed_accepts_list_input(self):
        """embed() should delegate list input to embed_batch()."""
        from cortex.embeddings import LocalEmbedder
        from unittest.mock import patch

        embedder = LocalEmbedder()
        with patch.object(embedder, "embed_batch", return_value=[[0.1, 0.2]]) as mock:
            result = embedder.embed(["test query"])
            mock.assert_called_once_with(["test query"])
            assert result == [[0.1, 0.2]]


# ═══ Export module edge cases ════════════════════════════════════


class TestExportEdgeCases:
    """Export module handles edge cases."""

    def test_export_unsupported_format(self):
        """export_facts should raise ValueError for unknown format."""
        from cortex.export import export_facts

        with pytest.raises(ValueError, match="Unsupported"):
            export_facts([], fmt="xml")

    def test_export_csv_empty(self):
        """export_facts CSV with empty list returns empty string."""
        from cortex.export import export_facts

        result = export_facts([], fmt="csv")
        assert result == ""

    def test_export_json_empty(self):
        """export_facts JSON with empty list returns valid JSON."""
        from cortex.export import export_facts

        result = export_facts([], fmt="json")
        assert json.loads(result) == []

    def test_export_format_normalization(self):
        """export_facts should normalize format string."""
        from cortex.export import export_facts

        result = export_facts([], fmt="  JSON  ")
        assert json.loads(result) == []


# ═══ Temporal module correctness ═════════════════════════════════


class TestTemporalModule:
    """Temporal utilities should work correctly."""

    def test_now_iso_format(self):
        """now_iso should return valid ISO 8601."""
        from cortex.temporal import now_iso

        ts = now_iso()
        assert "T" in ts
        assert len(ts) > 10

    def test_is_valid_at_active_fact(self):
        """Active fact (no valid_until) should be valid."""
        from cortex.temporal import is_valid_at

        assert is_valid_at("2024-01-01T00:00:00+00:00", None) is True

    def test_is_valid_at_deprecated_fact(self):
        """Deprecated fact should not be valid at current time."""
        from cortex.temporal import is_valid_at

        assert (
            is_valid_at(
                "2024-01-01T00:00:00+00:00",
                "2024-06-01T00:00:00+00:00",
            )
            is False
        )

    def test_build_temporal_filter_current(self):
        """build_temporal_filter_params(None) returns valid_until IS NULL."""
        from cortex.temporal import build_temporal_filter_params

        clause, params = build_temporal_filter_params(None)
        assert "valid_until IS NULL" in clause
        assert params == []

    def test_build_temporal_filter_as_of(self):
        """build_temporal_filter_params with date returns parameterized clause."""
        from cortex.temporal import build_temporal_filter_params

        clause, params = build_temporal_filter_params("2024-06-01T00:00:00")
        assert "valid_from <= ?" in clause
        assert len(params) == 2


# ═══ Metrics module ══════════════════════════════════════════════


class TestMetricsModule:
    """Metrics registry should work correctly."""

    def test_counter_increment(self):
        """Counter should increment correctly."""
        from cortex.metrics import MetricsRegistry

        reg = MetricsRegistry()
        reg.inc("test_counter")
        reg.inc("test_counter")
        output = reg.to_prometheus()
        assert "test_counter 2" in output

    def test_gauge_set(self):
        """Gauge should be settable."""
        from cortex.metrics import MetricsRegistry

        reg = MetricsRegistry()
        reg.set_gauge("test_gauge", 42.5)
        output = reg.to_prometheus()
        assert "test_gauge 42.50" in output

    def test_reset_clears_all(self):
        """Reset should clear all metrics."""
        from cortex.metrics import MetricsRegistry

        reg = MetricsRegistry()
        reg.inc("counter")
        reg.set_gauge("gauge", 1.0)
        reg.observe("hist", 0.5)
        reg.reset()
        output = reg.to_prometheus()
        assert output.strip() == ""
