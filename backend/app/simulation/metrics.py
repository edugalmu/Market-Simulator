from app.core.events import OrderSide


def calculate_spread_bps(*, best_bid: float, best_ask: float, mid_price: float) -> float:
    if mid_price <= 0:
        return 0.0
    return round(((best_ask - best_bid) / mid_price) * 10_000, 4)


def calculate_market_cap(*, mark_price: float, total_asset_inventory: float) -> float:
    return round(mark_price * total_asset_inventory, 2)


def quantity_for_notional(*, notional: float, price: float) -> float:
    if notional <= 0 or price <= 0:
        return 0.0
    return round(max(notional / price, 0.0001), 6)


def calculate_trade_execution_pnl(*, side: OrderSide, quantity: float, price_before: float, average_fill_price: float) -> float:
    if quantity <= 1e-9 or price_before <= 0 or average_fill_price <= 0:
        return 0.0

    if side == OrderSide.BUY:
        return round((price_before - average_fill_price) * quantity, 6)

    return round((average_fill_price - price_before) * quantity, 6)
