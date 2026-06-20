from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class BookLevel:
    price: float
    quantity: float
    orders: int


class OrderBook:
    def __init__(self) -> None:
        self.bids: list[BookLevel] = []
        self.asks: list[BookLevel] = []

    def clone(self) -> "OrderBook":
        cloned = OrderBook()
        cloned.bids = deepcopy(self.bids)
        cloned.asks = deepcopy(self.asks)
        return cloned

    def seed_around(
        self,
        reference_price: float,
        *,
        levels: int = 8,
        spacing_bps: float = 10.0,
        base_quantity: float = 12.0,
    ) -> None:
        self.bids = []
        self.asks = []

        for index in range(levels):
            offset = reference_price * ((index + 1) * spacing_bps / 10_000)
            quantity = round(base_quantity * (1 + index * 0.2), 4)
            orders = max(1, 5 + index * 2)
            self.bids.append(BookLevel(price=round(reference_price - offset, 2), quantity=quantity, orders=orders))
            self.asks.append(BookLevel(price=round(reference_price + offset, 2), quantity=quantity, orders=orders))

        self.bids.sort(key=lambda level: level.price, reverse=True)
        self.asks.sort(key=lambda level: level.price)

    def ensure_depth_around(
        self,
        reference_price: float,
        *,
        levels: int = 8,
        spacing_bps: float = 10.0,
        base_quantity: float = 6.0,
    ) -> None:
        for index in range(levels):
            offset = reference_price * ((index + 1) * spacing_bps / 10_000)
            quantity = round(base_quantity * (1 + index * 0.18), 4)
            orders = max(1, 4 + index * 2)
            bid_price = round(reference_price - offset, 2)
            ask_price = round(reference_price + offset, 2)
            self._ensure_level(
                self.bids,
                price=bid_price,
                target_quantity=quantity,
                target_orders=orders,
                reverse=True,
            )
            self._ensure_level(
                self.asks,
                price=ask_price,
                target_quantity=quantity,
                target_orders=orders,
                reverse=False,
            )

    @property
    def best_bid(self) -> float | None:
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> float | None:
        return self.asks[0].price if self.asks else None

    @property
    def mid_price(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return round((self.best_bid + self.best_ask) / 2, 4)

    @property
    def bid_depth(self) -> float:
        return round(sum(level.quantity for level in self.bids), 4)

    @property
    def ask_depth(self) -> float:
        return round(sum(level.quantity for level in self.asks), 4)

    def snapshot(self, *, depth: int = 5) -> tuple[list[BookLevel], list[BookLevel]]:
        return self.bids[:depth], self.asks[:depth]

    @staticmethod
    def _ensure_level(
        levels: list[BookLevel],
        *,
        price: float,
        target_quantity: float,
        target_orders: int,
        reverse: bool,
    ) -> None:
        for index, level in enumerate(levels):
            if level.price != price:
                continue

            if level.quantity < target_quantity or level.orders < target_orders:
                levels[index] = BookLevel(
                    price=price,
                    quantity=max(level.quantity, target_quantity),
                    orders=max(level.orders, target_orders),
                )
            break
        else:
            levels.append(BookLevel(price=price, quantity=target_quantity, orders=target_orders))

        levels.sort(key=lambda level: level.price, reverse=reverse)
