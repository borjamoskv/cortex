"""
CORTEX v4.0 — Temporal Module Tests.

Tests for now_iso, is_valid_at and build_temporal_filter_params.
"""

from cortex.temporal import build_temporal_filter_params, is_valid_at, now_iso


class TestNowIso:
    def test_returns_string(self):
        result = now_iso()
        assert isinstance(result, str)

    def test_contains_t_separator(self):
        result = now_iso()
        assert "T" in result

    def test_contains_timezone(self):
        result = now_iso()
        # Should contain timezone offset (+00:00 or Z)
        assert "+" in result or "Z" in result


class TestIsValidAt:
    def test_active_fact_is_valid(self):
        """A fact with no valid_until is still active."""
        assert is_valid_at("2024-01-01T00:00:00+00:00", None, "2025-01-01T00:00:00+00:00")

    def test_future_fact_is_not_valid(self):
        """A fact that hasn't started yet is not valid."""
        assert not is_valid_at("2026-01-01T00:00:00+00:00", None, "2025-01-01T00:00:00+00:00")

    def test_deprecated_fact_before_expiry(self):
        """A deprecated fact is valid before its valid_until."""
        assert is_valid_at(
            "2024-01-01T00:00:00+00:00",
            "2025-06-01T00:00:00+00:00",
            "2025-01-01T00:00:00+00:00",
        )

    def test_deprecated_fact_after_expiry(self):
        """A deprecated fact is not valid after its valid_until."""
        assert not is_valid_at(
            "2024-01-01T00:00:00+00:00",
            "2025-01-01T00:00:00+00:00",
            "2025-06-01T00:00:00+00:00",
        )

    def test_exact_boundary_valid_from(self):
        """At exact valid_from, fact is valid."""
        assert is_valid_at("2025-01-01T00:00:00+00:00", None, "2025-01-01T00:00:00+00:00")

    def test_exact_boundary_valid_until(self):
        """At exact valid_until, fact is no longer valid (half-open interval)."""
        assert not is_valid_at(
            "2024-01-01T00:00:00+00:00",
            "2025-01-01T00:00:00+00:00",
            "2025-01-01T00:00:00+00:00",
        )

    def test_none_at_uses_now(self):
        """When 'at' is None, defaults to now — should be valid for past start."""
        assert is_valid_at("2020-01-01T00:00:00+00:00", None, None)


class TestBuildTemporalFilterParams:
    def test_none_returns_current_filter(self):
        """None yields 'valid_until IS NULL' with no params."""
        clause, params = build_temporal_filter_params(None)
        assert clause == "valid_until IS NULL"
        assert params == []

    def test_as_of_returns_range_filter(self):
        """Providing as_of yields a range filter with 2 params."""
        ts = "2025-01-01T00:00:00+00:00"
        clause, params = build_temporal_filter_params(ts)
        assert "valid_from <= ?" in clause
        assert "valid_until" in clause
        assert params == [ts, ts]
