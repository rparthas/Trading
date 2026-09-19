"""Trade analysis and plan schemas — the contract between engine and UI/LLM."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class GateType(str, Enum):
    MANDATORY = "mandatory"
    CONFIRMATORY = "confirmatory"


class Decision(str, Enum):
    TRADE = "TRADE"
    NO_TRADE = "NO_TRADE"


class GateResult(BaseModel):
    gate: str
    gate_type: GateType
    passed: bool
    value: Any = None
    threshold: Any = None
    message: str = ""


class PatternResult(BaseModel):
    pattern: str
    direction: Direction
    strength: float = Field(ge=0.0, le=1.0)
    candle_index: int
    entry_reference: float
    stop_reference: float
    validation: dict[str, float] = Field(default_factory=dict)


class RejectionReason(BaseModel):
    symbol: str
    pattern: str | None = None
    failed_gate: str
    message: str
    gate_results: list[GateResult] = Field(default_factory=list)


class TradePlan(BaseModel):
    symbol: str
    direction: Direction
    pattern: str
    prior_trend: str
    entry: float
    stop: float
    target: float
    rr: float
    volume_ratio: float
    support: float | None = None
    resistance: float | None = None
    shares: int
    holding_period_days: tuple[int, int] = (3, 10)
    macd: str | None = None
    rsi: float | None = None
    decision: Decision = Decision.TRADE
    strategy_version: str = "1.0.0"
    data_timestamp: datetime | None = None
    scan_date: date | None = None


class TradeAnalysis(BaseModel):
    symbol: str
    scan_date: date
    decision: Decision
    pattern: PatternResult | None = None
    gate_results: list[GateResult] = Field(default_factory=list)
    trade_plan: TradePlan | None = None
    rejection: RejectionReason | None = None


class ScanResult(BaseModel):
    scan_date: date
    universe: str
    candidates: int = 0
    qualified: list[TradePlan] = Field(default_factory=list)
    rejected: list[RejectionReason] = Field(default_factory=list)
    no_pattern: list[str] = Field(default_factory=list)
    strategy_version: str = "1.0.0"
    data_timestamp: datetime | None = None
