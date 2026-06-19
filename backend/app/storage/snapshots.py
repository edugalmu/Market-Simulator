from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SnapshotRecord:
    session_id: str
    tick: int
    mid_price: float
