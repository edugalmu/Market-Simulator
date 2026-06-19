from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class MarketEventType(str, Enum):
    SNAPSHOT = "snapshot"
    SHOCK = "shock"
    ORDER_ACCEPTED = "order_accepted"
    TRADE = "trade"


@dataclass(slots=True, frozen=True)
class MarketEvent:
    event_type: MarketEventType
    tick: int
    payload: dict[str, object]
