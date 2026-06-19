def calculate_spread_bps(*, best_bid: float, best_ask: float, mid_price: float) -> float:
    if mid_price <= 0:
        return 0.0
    return round(((best_ask - best_bid) / mid_price) * 10_000, 4)


def calculate_market_cap(*, mark_price: float, total_asset_inventory: float) -> float:
    return round(mark_price * total_asset_inventory, 2)
