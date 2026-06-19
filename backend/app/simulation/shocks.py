from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(slots=True, frozen=True)
class ShockCommand:
    shock_type: Literal["whale_buy", "whale_sell", "liquidity_pull", "panic_wave"]
    magnitude: float
