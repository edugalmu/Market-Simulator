from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SessionRecord:
    session_id: str
    status: str
    seed: int
