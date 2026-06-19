from __future__ import annotations

from dataclasses import dataclass, field

from app.core.events import MarketEvent


@dataclass(slots=True)
class EventLog:
    events: list[MarketEvent] = field(default_factory=list)

    def append(self, event: MarketEvent) -> None:
        self.events.append(event)
