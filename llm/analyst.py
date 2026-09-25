"""OpenAI analyst — explains TradePlan objects without changing numbers."""

from __future__ import annotations

import os
import re
from typing import Iterable

from llm.prompts import SYSTEM_PROMPT, build_user_message
from models.trade import TradePlan

_NUMBER_PATTERN = re.compile(r"(?<![\w.])(?:\d+\.\d+|\d+)(?:%)?")
_FLOAT_TOLERANCE = 1e-4


def _openai_base_url() -> str | None:
    """OpenAI-compatible API base URL (optional; defaults to api.openai.com)."""
    for name in ("OPENAI_BASE_URL", "OPENAI_API_BASE"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def _openai_client():
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    kwargs: dict[str, str] = {"api_key": api_key}
    base_url = _openai_base_url()
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def explain_trade(plan: TradePlan) -> str:
    """Return a human-readable trade explanation."""
    template = _template_explanation(plan)
    try:
        client = _openai_client()
    except ImportError:
        return template
    if client is None:
        return template

    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_message(plan)},
        ],
        temperature=0.2,
    )
    text = (response.choices[0].message.content or "").strip()
    if text and numbers_are_valid(plan, text):
        return text
    return template


def numbers_are_valid(plan: TradePlan, text: str) -> bool:
    """Ensure every number in the model output matches the trade plan."""
    allowed = _plan_numbers(plan)
    for token in _extract_numbers(text):
        if not _matches_allowed(token, allowed):
            return False
    return True


def _plan_numbers(plan: TradePlan) -> set[float]:
    values: set[float] = {
        float(plan.entry),
        float(plan.stop),
        float(plan.target),
        float(plan.rr),
        float(plan.volume_ratio),
        float(plan.shares),
        float(plan.holding_period_days[0]),
        float(plan.holding_period_days[1]),
    }
    if plan.support is not None:
        values.add(float(plan.support))
    if plan.resistance is not None:
        values.add(float(plan.resistance))
    if plan.rsi is not None:
        values.add(float(plan.rsi))
    return values


def _extract_numbers(text: str) -> list[float]:
    numbers: list[float] = []
    for match in _NUMBER_PATTERN.finditer(text):
        token = match.group(0).rstrip("%")
        numbers.append(float(token))
    return numbers


def _matches_allowed(value: float, allowed: Iterable[float]) -> bool:
    return any(abs(value - candidate) <= _FLOAT_TOLERANCE for candidate in allowed)


def _template_explanation(plan: TradePlan) -> str:
    support = plan.support if plan.support is not None else "n/a"
    resistance = plan.resistance if plan.resistance is not None else "n/a"
    macd = plan.macd if plan.macd is not None else "n/a"
    rsi = plan.rsi if plan.rsi is not None else "n/a"
    hold_min, hold_max = plan.holding_period_days

    return f"""## Thesis
{plan.symbol} shows a {plan.pattern.replace("_", " ")} setup in a {plan.prior_trend} context. The engine qualified a {plan.direction.value} trade.

## Evidence
- Entry: {plan.entry}
- Stop: {plan.stop}
- Target: {plan.target}
- Risk/reward: {plan.rr}
- Volume ratio: {plan.volume_ratio}x
- Support: {support}
- Resistance: {resistance}
- MACD: {macd}
- RSI: {rsi}
- Position size: {plan.shares} shares

## Risks
The stop at {plan.stop} defines the risk boundary. A close beyond that level invalidates the pattern-based thesis.

## Invalidation
Exit or reassess if price trades through the stop ({plan.stop}) before reaching the target ({plan.target}).

## Summary
Planned {plan.direction.value} on {plan.symbol} from {plan.entry} with stop {plan.stop}, target {plan.target}, and expected holding window of {hold_min}–{hold_max} days.
"""
