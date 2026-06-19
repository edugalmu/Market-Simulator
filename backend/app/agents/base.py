from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class StrategyType(str, Enum):
    NOISE = "noise"
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    MARKET_MAKER = "market_maker"
    FUNDAMENTAL = "fundamental"


@dataclass(slots=True, frozen=True)
class AgentProfile:
    agent_id: int
    strategy: StrategyType
    initial_cash: float
    initial_asset: float
