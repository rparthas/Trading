"""Tests for the LLM analyst layer (no live API calls)."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from llm.analyst import explain_trade, numbers_are_valid
from models.trade import Direction, TradePlan


@pytest.fixture
def sample_plan() -> TradePlan:
    return TradePlan(
        symbol="RELIANCE",
        direction=Direction.LONG,
        pattern="bullish_hammer",
        prior_trend="downtrend",
        entry=1455.0,
        stop=1418.0,
        target=1520.0,
        rr=1.76,
        volume_ratio=1.42,
        support=1420.0,
        resistance=1530.0,
        shares=135,
        macd="bullish",
        rsi=54.0,
        scan_date=date(2026, 9, 19),
    )


def test_template_explanation_without_api_key(sample_plan, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    explanation = explain_trade(sample_plan)
    assert "1455" in explanation
    assert "1418" in explanation
    assert "1520" in explanation
    assert "1.76" in explanation
    assert "Thesis" in explanation


def test_numbers_are_valid_accepts_plan_values(sample_plan):
    text = (
        f"Entry {sample_plan.entry}, stop {sample_plan.stop}, "
        f"target {sample_plan.target}, R:R {sample_plan.rr}, "
        f"size {sample_plan.shares} shares over 3-10 days."
    )
    assert numbers_are_valid(sample_plan, text)


def test_numbers_are_valid_rejects_altered_values(sample_plan):
    text = f"Entry {sample_plan.entry + 1}, stop {sample_plan.stop}, target {sample_plan.target}"
    assert not numbers_are_valid(sample_plan, text)


@patch("openai.OpenAI")
def test_explain_trade_uses_openai_when_key_present(mock_openai_cls, sample_plan, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content=(
                        "## Thesis\n"
                        f"Entry {sample_plan.entry}, stop {sample_plan.stop}, "
                        f"target {sample_plan.target}, R:R {sample_plan.rr}."
                    )
                )
            )
        ]
    )

    explanation = explain_trade(sample_plan)
    assert str(sample_plan.entry) in explanation
    mock_client.chat.completions.create.assert_called_once()


@patch("openai.OpenAI")
def test_explain_trade_falls_back_on_invalid_numbers(mock_openai_cls, sample_plan, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    mock_client = MagicMock()
    mock_openai_cls.return_value = mock_client
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="Entry 9999, stop 1418, target 1520."))]
    )

    explanation = explain_trade(sample_plan)
    assert "9999" not in explanation
    assert str(sample_plan.entry) in explanation
