from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class StrategyType(str, Enum):
    NOISE = "noise"
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    VALUE = "value"
    MARKET_MAKER = "market_maker"
    DIRECTIONAL_FUND = "directional_fund"
    AGGRESSIVE_WHALE = "aggressive_whale"
    FUNDAMENTAL = "fundamental"


@dataclass(slots=True, frozen=True)
class AgentProfile:
    agent_id: int
    strategy: StrategyType
    initial_cash: float
    initial_asset: float
