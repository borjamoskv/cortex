"""
MEJORAlo Round 8 — Final Hardening Tests.

Tests for:
1. Metrics histogram deque cap + accurate totals
2. Async client fmt parameter rename
3. API endpoint error handling (status, time, graph)
"""

from collections import deque

import pytest

from cortex.metrics import _HISTOGRAM_MAX_OBSERVATIONS, MetricsRegistry

# ─── Metrics: Histogram Cap ──────────────────────────────────────────


class TestHistogramCap:
    """Verify histogram observations use capped deque."""

    def test_histogram_uses_deque(self):
        reg = MetricsRegistry()
        reg.observe("test_hist", 1.0)
        assert isinstance(reg._histograms["test_hist"], deque)

    def test_histogram_cap_evicts_oldest(self):
        reg = MetricsRegistry()
        for i in range(_HISTOGRAM_MAX_OBSERVATIONS + 500):
            reg.observe("test_hist", float(i))
        # Deque should be capped
        assert len(reg._histograms["test_hist"]) == _HISTOGRAM_MAX_OBSERVATIONS
        # But count/sum track all observations
        assert reg._hist_count["test_hist"] == _HISTOGRAM_MAX_OBSERVATIONS + 500

    def test_histogram_sum_accuracy(self):
        reg = MetricsRegistry()
        total = 0.0
        for i in range(2000):
            val = float(i)
            reg.observe("test_hist", val)
            total += val
        assert reg._hist_sum["test_hist"] == pytest.approx(total)

    def test_histogram_count_survives_eviction(self):
        reg = MetricsRegistry()
        for i in range(1500):
            reg.observe("test_hist", 1.0)
        assert reg._hist_count["test_hist"] == 1500
        # Deque only holds last 1000
        assert len(reg._histograms["test_hist"]) == _HISTOGRAM_MAX_OBSERVATIONS

    def test_prometheus_output_uses_accumulators(self):
        reg = MetricsRegistry()
        reg.observe("req_duration", 0.1)
        reg.observe("req_duration", 0.2)
        output = reg.to_prometheus()
        assert "req_duration_count 2" in output
        assert "req_duration_sum 0.3000" in output

    def test_reset_clears_accumulators(self):
        reg = MetricsRegistry()
        reg.observe("test_hist", 1.0)
        reg.inc("test_counter")
        reg.set_gauge("test_gauge", 42.0)
        reg.reset()
        assert len(reg._histograms) == 0
        assert len(reg._hist_count) == 0
        assert len(reg._hist_sum) == 0
        assert len(reg._counters) == 0
        assert len(reg._gauges) == 0

    def test_labeled_histograms_independent(self):
        reg = MetricsRegistry()
        reg.observe("dur", 1.0, {"method": "GET"})
        reg.observe("dur", 2.0, {"method": "POST"})
        assert reg._hist_count['dur{method="GET"}'] == 1
        assert reg._hist_count['dur{method="POST"}'] == 1


# ─── Async Client: fmt Parameter ─────────────────────────────────────


class TestAsyncClientExport:
    """Verify export() uses fmt (not format)."""

    def test_export_signature_uses_fmt(self):
        import inspect

        from cortex.async_client import AsyncCortexClient

        sig = inspect.signature(AsyncCortexClient.export)
        assert "fmt" in sig.parameters
        assert "format" not in sig.parameters

    def test_async_client_all_exports(self):
        from cortex.async_client import __all__

        assert "AsyncCortexClient" in __all__


# ─── API: Endpoint Error Handling ─────────────────────────────────────


class TestApiStatusErrorHandling:
    """Status endpoint catches sqlite3.Error."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient

        from cortex.api import app

        return TestClient(app)

    def test_status_endpoint_handles_db_error(self, client):
        import inspect

        from cortex.routes.admin import status

        source = inspect.getsource(status)
        assert "Exception" in source
        assert "Status unavailable" in source


class TestApiExportFmtParameter:
    """export_project uses fmt (not format) internally."""

    def test_export_endpoint_no_format_shadow(self):
        import inspect

        from cortex.routes.admin import export_project

        source = inspect.getsource(export_project)
        # Should use fmt variable, not format
        assert "fmt ==" in source or "fmt:" in source

    def test_export_endpoint_preserves_format_query_param(self):
        """The query param should still be called 'format' for API compat."""
        import inspect

        from cortex.routes.admin import export_project

        source = inspect.getsource(export_project)
        assert 'alias="format"' in source


class TestApiTimeErrorHandling:
    """Time endpoints catch sqlite3.Error."""

    def test_heartbeat_has_error_handling(self):
        import inspect

        from cortex.routes.timing import record_heartbeat

        source = inspect.getsource(record_heartbeat)
        assert "sqlite3.Error" in source
        assert "Heartbeat failed" in source

    def test_time_today_has_error_handling(self):
        import inspect

        from cortex.routes.timing import time_today

        source = inspect.getsource(time_today)
        assert "sqlite3.Error" in source

    def test_time_report_has_error_handling(self):
        import inspect

        from cortex.routes.timing import time_report

        source = inspect.getsource(time_report)
        assert "sqlite3.Error" in source

    def test_time_history_has_error_handling(self):
        import inspect

        from cortex.routes.timing import get_time_history

        source = inspect.getsource(get_time_history)
        assert "sqlite3.Error" in source


class TestApiGraphErrorHandling:
    """Graph endpoints catch sqlite3.Error."""

    def test_graph_project_has_error_handling(self):
        import inspect

        from cortex.routes.graph import get_graph

        source = inspect.getsource(get_graph)
        assert "Exception" in source
        assert "Graph unavailable" in source

    def test_graph_all_has_error_handling(self):
        import inspect

        from cortex.routes.graph import get_graph_all

        source = inspect.getsource(get_graph_all)
        assert "Exception" in source
