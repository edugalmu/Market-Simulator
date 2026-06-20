from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from random import Random

from app.core.events import OrderSide


@dataclass(slots=True, frozen=True)
class BookLevel:
    price: float
    quantity: float
    orders: int


@dataclass(slots=True)
class BookOrder:
    order_id: int
    agent_id: int
    strategy_type: str
    side: OrderSide
    price: float
    quantity: float
    created_tick: int
    ttl_ticks: int
    is_iceberg: bool = False
    display_quantity: float | None = None
    hidden_quantity: float = 0.0
    replenish_quantity: float = 0.0
    initial_hidden_quantity: float = 0.0


class OrderBook:
    def __init__(self) -> None:
        self.bid_orders: list[BookOrder] = []
        self.ask_orders: list[BookOrder] = []
        self._next_order_id = 1

    def clone(self) -> "OrderBook":
        cloned = OrderBook()
        cloned.bid_orders = deepcopy(self.bid_orders)
        cloned.ask_orders = deepcopy(self.ask_orders)
        cloned._next_order_id = self._next_order_id
        return cloned

    @property
    def bids(self) -> list[BookLevel]:
        return self._aggregate_levels(self.bid_orders, reverse=True)

    @property
    def asks(self) -> list[BookLevel]:
        return self._aggregate_levels(self.ask_orders, reverse=False)

    @property
    def best_bid(self) -> float | None:
        levels = self.bids
        return levels[0].price if levels else None

    @property
    def best_ask(self) -> float | None:
        levels = self.asks
        return levels[0].price if levels else None

    @property
    def mid_price(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return round((self.best_bid + self.best_ask) / 2, 4)

    @property
    def bid_depth(self) -> float:
        return round(sum(order.quantity for order in self.bid_orders), 4)

    @property
    def ask_depth(self) -> float:
        return round(sum(order.quantity for order in self.ask_orders), 4)

    def seed_around(
        self,
        reference_price: float,
        *,
        levels: int = 8,
        spacing_bps: float = 10.0,
        base_quantity: float = 12.0,
        created_tick: int = 0,
        ttl_ticks: int = 10_000,
    ) -> None:
        self.bid_orders = []
        self.ask_orders = []

        for index in range(levels):
            offset = reference_price * ((index + 1) * spacing_bps / 10_000)
            quantity = round(base_quantity * (1 + index * 0.2), 4)
            order_count = max(1, 5 + index * 2)
            self._seed_level(
                side=OrderSide.BUY,
                price=round(reference_price - offset, 2),
                total_quantity=quantity,
                order_count=order_count,
                created_tick=created_tick,
                ttl_ticks=ttl_ticks,
                strategy_type="seed",
            )
            self._seed_level(
                side=OrderSide.SELL,
                price=round(reference_price + offset, 2),
                total_quantity=quantity,
                order_count=order_count,
                created_tick=created_tick,
                ttl_ticks=ttl_ticks,
                strategy_type="seed",
            )

    def ensure_depth_around(
        self,
        reference_price: float,
        *,
        levels: int = 8,
        spacing_bps: float = 10.0,
        base_quantity: float = 6.0,
        created_tick: int = 0,
        ttl_ticks: int = 12,
        strategy_type: str = "market_maker",
        rng: Random | None = None,
        gap_probability: float = 0.0,
    ) -> None:
        for index in range(levels):
            if rng is not None and gap_probability > 0:
                distance_multiplier = 0.55 + (index / max(levels - 1, 1)) * 0.9
                if rng.random() < min(gap_probability * distance_multiplier, 0.9):
                    continue

            offset = reference_price * ((index + 1) * spacing_bps / 10_000)
            quantity = round(base_quantity * (1 + index * 0.18), 4)
            target_orders = max(1, 4 + index * 2)
            self._ensure_level(
                side=OrderSide.BUY,
                price=round(reference_price - offset, 2),
                target_quantity=quantity,
                target_orders=target_orders,
                created_tick=created_tick,
                ttl_ticks=ttl_ticks,
                strategy_type=strategy_type,
            )
            self._ensure_level(
                side=OrderSide.SELL,
                price=round(reference_price + offset, 2),
                target_quantity=quantity,
                target_orders=target_orders,
                created_tick=created_tick,
                ttl_ticks=ttl_ticks,
                strategy_type=strategy_type,
            )

    def add_limit_order(
        self,
        *,
        side: OrderSide,
        price: float,
        quantity: float,
        agent_id: int,
        strategy_type: str,
        created_tick: int,
        ttl_ticks: int,
    ) -> int | None:
        normalized_quantity = round(quantity, 6)
        if normalized_quantity <= 1e-9:
            return None

        order = BookOrder(
            order_id=self._next_order_id,
            agent_id=agent_id,
            strategy_type=strategy_type,
            side=side,
            price=round(price, 2),
            quantity=normalized_quantity,
            created_tick=created_tick,
            ttl_ticks=max(ttl_ticks, 1),
        )
        self._next_order_id += 1
        self._orders_for(side).append(order)
        self._sort_orders(side)
        return order.order_id

    def add_iceberg_order(
        self,
        *,
        side: OrderSide,
        price: float,
        display_quantity: float,
        hidden_quantity: float,
        replenish_quantity: float,
        agent_id: int,
        strategy_type: str,
        created_tick: int,
        ttl_ticks: int,
    ) -> int | None:
        visible_quantity = round(display_quantity, 6)
        hidden_quantity = round(hidden_quantity, 6)
        replenish_quantity = round(replenish_quantity, 6)
        if visible_quantity <= 1e-9:
            return None

        order = BookOrder(
            order_id=self._next_order_id,
            agent_id=agent_id,
            strategy_type=strategy_type,
            side=side,
            price=round(price, 2),
            quantity=visible_quantity,
            created_tick=created_tick,
            ttl_ticks=max(ttl_ticks, 1),
            is_iceberg=True,
            display_quantity=visible_quantity,
            hidden_quantity=max(hidden_quantity, 0.0),
            replenish_quantity=max(replenish_quantity, visible_quantity),
            initial_hidden_quantity=max(hidden_quantity, 0.0),
        )
        self._next_order_id += 1
        self._orders_for(side).append(order)
        self._sort_orders(side)
        return order.order_id

    def expire_orders(self) -> int:
        removed = 0
        for orders in (self.bid_orders, self.ask_orders):
            for order in orders:
                order.ttl_ticks -= 1

            before_count = len(orders)
            orders[:] = [order for order in orders if order.ttl_ticks > 0 and order.quantity > 1e-9]
            removed += before_count - len(orders)

        return removed

    def cancel_random_orders(
        self,
        *,
        rng: Random,
        max_ratio: float,
        min_age_ticks: int,
        current_tick: int,
        strategy_type: str | None = None,
    ) -> int:
        removed = 0
        for side in (OrderSide.BUY, OrderSide.SELL):
            orders = self._orders_for(side)
            candidates = [
                order
                for order in orders
                if current_tick - order.created_tick >= min_age_ticks
                and (strategy_type is None or order.strategy_type == strategy_type)
            ]
            if not candidates:
                continue

            cancel_count = min(len(candidates), max(int(len(candidates) * max_ratio), 1))
            for order in rng.sample(candidates, k=cancel_count):
                if self.cancel_order(order.order_id):
                    removed += 1

        return removed

    def cancel_order(self, order_id: int) -> bool:
        for orders in (self.bid_orders, self.ask_orders):
            for index, order in enumerate(orders):
                if order.order_id != order_id:
                    continue

                orders.pop(index)
                return True

        return False

    def cancel_orders_for_agent(
        self,
        *,
        agent_id: int,
        side: OrderSide | None = None,
        max_cancel: int | None = None,
    ) -> int:
        sides = [side] if side is not None else [OrderSide.BUY, OrderSide.SELL]
        removed = 0
        for current_side in sides:
            orders = self._orders_for(current_side)
            indices = [index for index, order in enumerate(orders) if order.agent_id == agent_id]
            if max_cancel is not None:
                indices = indices[:max_cancel]

            for index in reversed(indices):
                orders.pop(index)
                removed += 1

        return removed

    def matching_orders(self, *, side: OrderSide) -> list[BookOrder]:
        self._sort_orders(side)
        return self._orders_for(side)

    def apply_order_fill(self, *, side: OrderSide, order_id: int, fill_quantity: float) -> None:
        orders = self._orders_for(side)
        for index, order in enumerate(orders):
            if order.order_id != order_id:
                continue

            order.quantity = round(order.quantity - fill_quantity, 6)
            if order.quantity <= 1e-9:
                if order.is_iceberg and order.hidden_quantity > 1e-9:
                    replenished_quantity = min(order.replenish_quantity, order.hidden_quantity)
                    order.hidden_quantity = round(order.hidden_quantity - replenished_quantity, 6)
                    order.quantity = round(replenished_quantity, 6)
                    order.display_quantity = round(replenished_quantity, 6)
                    return

                orders.pop(index)
            return

        raise LookupError(f"Order {order_id} not found in {side.value} book.")

    def snapshot(self, *, depth: int = 5) -> tuple[list[BookLevel], list[BookLevel]]:
        return self.bids[:depth], self.asks[:depth]

    def _seed_level(
        self,
        *,
        side: OrderSide,
        price: float,
        total_quantity: float,
        order_count: int,
        created_tick: int,
        ttl_ticks: int,
        strategy_type: str,
    ) -> None:
        remaining_quantity = round(total_quantity, 6)
        for index in range(order_count):
            slice_count = order_count - index
            slice_quantity = round(remaining_quantity / slice_count, 6)
            remaining_quantity = round(remaining_quantity - slice_quantity, 6)
            self.add_limit_order(
                side=side,
                price=price,
                quantity=slice_quantity,
                agent_id=0,
                strategy_type=strategy_type,
                created_tick=created_tick,
                ttl_ticks=ttl_ticks,
            )

    def _ensure_level(
        self,
        *,
        side: OrderSide,
        price: float,
        target_quantity: float,
        target_orders: int,
        created_tick: int,
        ttl_ticks: int,
        strategy_type: str,
    ) -> None:
        current_orders = [order for order in self._orders_for(side) if order.price == price]
        current_quantity = sum(order.quantity for order in current_orders)
        missing_quantity = round(max(target_quantity - current_quantity, 0.0), 6)
        if missing_quantity <= 1e-9:
            return

        orders_to_add = max(target_orders - len(current_orders), 1)
        remaining_quantity = missing_quantity
        for index in range(orders_to_add):
            slice_count = orders_to_add - index
            slice_quantity = round(remaining_quantity / slice_count, 6)
            remaining_quantity = round(remaining_quantity - slice_quantity, 6)
            self.add_limit_order(
                side=side,
                price=price,
                quantity=slice_quantity,
                agent_id=0,
                strategy_type=strategy_type,
                created_tick=created_tick,
                ttl_ticks=ttl_ticks,
            )

    def _orders_for(self, side: OrderSide) -> list[BookOrder]:
        return self.bid_orders if side == OrderSide.BUY else self.ask_orders

    def _sort_orders(self, side: OrderSide) -> None:
        orders = self._orders_for(side)
        if side == OrderSide.BUY:
            orders.sort(key=lambda order: (-order.price, order.created_tick, order.order_id))
            return

        orders.sort(key=lambda order: (order.price, order.created_tick, order.order_id))

    @staticmethod
    def _aggregate_levels(orders: list[BookOrder], *, reverse: bool) -> list[BookLevel]:
        grouped: dict[float, list[BookOrder]] = defaultdict(list)
        for order in orders:
            grouped[order.price].append(order)

        levels = [
            BookLevel(
                price=price,
                quantity=round(sum(order.quantity for order in grouped_orders), 6),
                orders=len(grouped_orders),
            )
            for price, grouped_orders in grouped.items()
        ]
        levels.sort(key=lambda level: level.price, reverse=reverse)
        return levels
