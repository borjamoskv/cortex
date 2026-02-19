import pytest
from click.testing import CliRunner

from cortex.chronos import ChronosEngine
from cortex.cli.chronos_cmds import analyze


def test_chronos_engine_math_low():
    """Test the low complexity math."""
    metrics = ChronosEngine.analyze(ai_time_secs=10, complexity="low")
    # Low multipliers: 1.5 + 1.0 + 2.0 + 0.5 + 0.0 = 5x
    # 10s * 5 = 50s. BUT baseline minimum for humans in low is 3 minutes (180s).
    assert metrics.ai_time_secs == 10
    assert metrics.human_time_secs == 180
    assert metrics.asymmetry_factor == 18.0
    assert metrics.tip in ChronosEngine.TIPS_POOL["low"]
    assert metrics.anti_tip in ChronosEngine.ANTI_TIPS_POOL["low"]


def test_chronos_engine_math_god():
    """Test the god complexity math."""
    metrics = ChronosEngine.analyze(ai_time_secs=120, complexity="god")
    # God multipliers: 10 + 15 + 5 + 15 + 5 = 50x
    # 120s * 50 = 6000s = 100 minutes. 
    # Baseline for god is 180 minutes (10800s).
    assert metrics.human_time_secs == 10800
    assert metrics.asymmetry_factor == 90.0
    assert metrics.tip in ChronosEngine.TIPS_POOL["god"]
    assert metrics.anti_tip in ChronosEngine.ANTI_TIPS_POOL["god"]


def test_chronos_engine_format_time():
    """Test time formatting."""
    assert ChronosEngine.format_time(45) == "45 segundos"
    assert ChronosEngine.format_time(120) == "2 minutos"
    assert ChronosEngine.format_time(7200) == "2.0 hrs"
    assert ChronosEngine.format_time(36000) == "1.2 días"  # 10 hours / 8


def test_chronos_engine_invalid_complexity():
    """Test unknown complexity raises ValueError."""
    with pytest.raises(ValueError):
        ChronosEngine.analyze(10, "super_god")


def test_cli_chronos_analyze():
    """Test the CLI command logic."""
    runner = CliRunner()
    result = runner.invoke(analyze, ["--ai-time", "15", "--complexity", "low"])
    assert result.exit_code == 0
    assert "CHRONOS-1 — SENIOR BENCHMARK" in result.output
    assert "Human Senior Time:" in result.output
    assert "MOSKV Swarm Time:" in result.output
    # Expect 15s to hit the 180s (3 min) human baseline. 180 / 15 = 12x
    assert "12.0x" in result.output

import json

def test_store_with_chronos(tmp_path):
    """Test storing a fact with CHRONOS auto-injection."""
    from cortex.engine import CortexEngine
    from cortex.cli.core import store

    db_path = tmp_path / "test.db"
    
    # Needs to be initialized first
    engine = CortexEngine(str(db_path))
    engine.init_db_sync()

    runner = CliRunner()
    result = runner.invoke(store, [
        "test_project",
        "This is a chronos test fact.",
        "--ai-time", "15",
        "--complexity", "low",
        "--db", str(db_path)
    ])
    
    assert result.exit_code == 0
    assert "Stored fact #1 in test_project" in result.output
    # Expect 15s low complexity to have 12.0x asymmetry
    assert "12.0x" in result.output
    
    # Verify the database explicitly
    conn = engine._get_sync_conn()
    row = conn.execute("SELECT meta FROM facts WHERE id = 1").fetchone()
    assert row is not None
    
    meta_dict = json.loads(row[0])
    assert "chronos" in meta_dict
    chronos_meta = meta_dict["chronos"]
    assert chronos_meta["ai_time_secs"] == 15
    assert chronos_meta["human_time_secs"] == 180
    assert chronos_meta["asymmetry_factor"] == 180 / 15
    
    engine.close_sync()
