"""Tests for strategy.yaml contract."""

from config import load_strategy, load_universe


def test_strategy_yaml_loads():
    cfg = load_strategy()
    assert cfg["risk_reward"]["minimum"] == 1.5
    assert cfg["support_resistance"]["max_stop_distance_pct"] == 4.0
    assert cfg["volume"]["minimum_ratio"] == 1.0


def test_nifty50_universe_count():
    symbols = load_universe()
    assert len(symbols) == 50
    assert "RELIANCE" in symbols
    assert "TCS" in symbols
