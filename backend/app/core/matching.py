from __future__ import annotations

from dataclasses import dataclass

from app.core.events import OrderSide
from app.core.order_book import OrderBook


@dataclass(slots=True, frozen=True)
class MatchResult:
    side: OrderSide
    requested_notional: float
    requested_quantity: float
    matched_notional: float
    trades_executed: int
    quantity_matched: float
    quantity_remaining: float
    average_fill_price: float


def execute_market_order(
    order_book: OrderBook,
    *,
    side: OrderSide,
    quantity: float,
) -> MatchResult:
    if quantity <= 0:
        raise ValueError("Market order quantity must be positive.")

    matched_quantity, matched_notional, trades_executed = _consume_orders(
        order_book,
        side=OrderSide.SELL if side == OrderSide.BUY else OrderSide.BUY,
        quantity=quantity,
    )

    average_fill_price = (
        round(matched_notional / matched_quantity, 6)
        if matched_quantity > 0
        else 0.0
    )

    return MatchResult(
        side=side,
        requested_notional=round(quantity * average_fill_price, 6)
        if average_fill_price > 0
        else 0.0,
        requested_quantity=round(quantity, 6),
        matched_notional=round(matched_notional, 6),
        trades_executed=trades_executed,
        quantity_matched=round(matched_quantity, 6),
        quantity_remaining=round(max(quantity - matched_quantity, 0.0), 6),
        average_fill_price=average_fill_price,
    )


def execute_market_buy_by_notional(
    order_book: OrderBook,
    *,
    notional: float,
    reference_price: float,
) -> MatchResult:
    if notional <= 0:
        raise ValueError("Market buy notional must be positive.")
    if reference_price <= 0:
        raise ValueError("Reference price must be positive.")

    remaining_notional = notional
    matched_quantity = 0.0
    matched_notional = 0.0
    trades_executed = 0

    ask_orders = order_book.matching_orders(side=OrderSide.SELL)
    while ask_orders and remaining_notional > 1e-9:
        order = ask_orders[0]
        affordable_quantity = remaining_notional / order.price
        fill_quantity = min(order.quantity, affordable_quantity)

        if fill_quantity <= 1e-9:
            break

        fill_notional = fill_quantity * order.price
        matched_quantity += fill_quantity
        matched_notional += fill_notional
        remaining_notional -= fill_notional
        trades_executed += 1

        order_book.apply_order_fill(
            side=OrderSide.SELL,
            order_id=order.order_id,
            fill_quantity=fill_quantity,
        )
        ask_orders = order_book.matching_orders(side=OrderSide.SELL)

    average_fill_price = (
        round(matched_notional / matched_quantity, 6)
        if matched_quantity > 0
        else 0.0
    )
    requested_quantity = round(notional / reference_price, 6)

    return MatchResult(
        side=OrderSide.BUY,
        requested_notional=round(notional, 6),
        requested_quantity=requested_quantity,
        matched_notional=round(matched_notional, 6),
        trades_executed=trades_executed,
        quantity_matched=round(matched_quantity, 6),
        quantity_remaining=round(max(requested_quantity - matched_quantity, 0.0), 6),
        average_fill_price=average_fill_price,
    )


def _consume_orders(
    order_book: OrderBook,
    *,
    side: OrderSide,
    quantity: float,
) -> tuple[float, float, int]:
    remaining_quantity = quantity
    matched_quantity = 0.0
    matched_notional = 0.0
    trades_executed = 0
    orders = order_book.matching_orders(side=side)

    while orders and remaining_quantity > 1e-9:
        order = orders[0]
        fill_quantity = min(order.quantity, remaining_quantity)
        matched_quantity += fill_quantity
        matched_notional += fill_quantity * order.price
        remaining_quantity -= fill_quantity
        trades_executed += 1

        order_book.apply_order_fill(side=side, order_id=order.order_id, fill_quantity=fill_quantity)
        orders = order_book.matching_orders(side=side)

    return matched_quantity, matched_notional, trades_executed
