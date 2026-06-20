from __future__ import annotations

from app.agents.registry import build_default_agent_profiles, summarize_agent_mix
from app.compute.backend import ComputeUnavailableError, resolve_compute_backend
from app.core.events import OrderSide
from app.core.ledger import Ledger
from app.core.matching import execute_market_buy_by_notional, execute_market_order
from app.core.order_book import OrderBook
from app.simulation.metrics import calculate_market_cap, calculate_spread_bps
from app.simulation.models import (
    AgentMixEntry,
    MarketMetrics,
    OrderBookLevel,
    OrderBookSnapshot,
    SessionConfig,
    SimulationSummary,
    WhaleBalanceSnapshot,
    WhaleShockOutcome,
    WhaleShockPreview,
)


WHALE_AGENT_ID = 0


class SimulationEngine:
    def __init__(self, *, gpu_enabled: bool) -> None:
        self.gpu_enabled = gpu_enabled

    def build_market_state(
        self,
        config: SessionConfig,
    ) -> tuple[str, list, Ledger, OrderBook]:
        return self._build_market_state(config)

    def build_order_book_snapshot(
        self,
        order_book: OrderBook,
        *,
        fallback_price: float,
    ) -> OrderBookSnapshot:
        return self._build_order_book_snapshot(order_book, fallback_price=fallback_price)

    def build_metrics(
        self,
        ledger: Ledger,
        order_book: OrderBook,
        active_backend: str,
        *,
        fallback_price: float,
    ) -> MarketMetrics:
        return self._build_metrics(
            ledger,
            order_book,
            active_backend,
            fallback_price=fallback_price,
        )

    def bootstrap_session(self, config: SessionConfig) -> SimulationSummary:
        active_backend, profiles, ledger, order_book = self._build_market_state(config)

        return SimulationSummary(
            session_id=f"bootstrap-{config.seed}-{config.agent_count}",
            status="bootstrap",
            config=config,
            agent_mix=[
                AgentMixEntry(strategy=strategy, count=count)
                for strategy, count in summarize_agent_mix(profiles).items()
            ],
            order_book=self._build_order_book_snapshot(order_book, fallback_price=config.initial_price),
            metrics=self._build_metrics(ledger, order_book, active_backend, fallback_price=config.initial_price),
            notes=[
                "This bootstrap session is deterministic and safe for frontend wiring.",
                "Whale shock preview is available through the simulation API.",
            ],
        )

    def preview_whale_shock(
        self,
        config: SessionConfig,
        *,
        side: OrderSide,
        notional: float,
    ) -> WhaleShockPreview:
        side = OrderSide(side)
        active_backend, _, ledger, order_book = self._build_market_state(config)
        book_before = self._build_order_book_snapshot(
            order_book,
            fallback_price=config.initial_price,
        )
        reference_price = book_before.mid_price or config.initial_price
        requested_quantity = round(notional / reference_price, 6)

        ledger.add_balance(
            WHALE_AGENT_ID,
            cash_free=notional if side == OrderSide.BUY else 0.0,
            asset_free=requested_quantity if side == OrderSide.SELL else 0.0,
        )
        whale_initial_cash = round(notional if side == OrderSide.BUY else 0.0, 6)
        whale_initial_asset = round(requested_quantity if side == OrderSide.SELL else 0.0, 6)
        whale_initial_total_equity = round(
            whale_initial_cash + whale_initial_asset * reference_price,
            6,
        )

        if side == OrderSide.BUY:
            ledger.reserve_cash(WHALE_AGENT_ID, notional)
            match_result = execute_market_buy_by_notional(
                order_book,
                notional=notional,
                reference_price=reference_price,
            )
            ledger.apply_buy_fill(
                WHALE_AGENT_ID,
                spent_cash=match_result.matched_notional,
                received_asset=match_result.quantity_matched,
            )
            ledger.release_cash(
                WHALE_AGENT_ID,
                ledger.get_balance(WHALE_AGENT_ID).cash_reserved,
            )
        else:
            ledger.reserve_asset(WHALE_AGENT_ID, requested_quantity)
            match_result = execute_market_order(
                order_book,
                side=side,
                quantity=requested_quantity,
            )
            match_result = match_result.__class__(
                side=match_result.side,
                requested_notional=round(notional, 6),
                requested_quantity=match_result.requested_quantity,
                matched_notional=match_result.matched_notional,
                trades_executed=match_result.trades_executed,
                quantity_matched=match_result.quantity_matched,
                quantity_remaining=match_result.quantity_remaining,
                average_fill_price=match_result.average_fill_price,
            )
            ledger.apply_sell_fill(
                WHALE_AGENT_ID,
                sold_asset=match_result.quantity_matched,
                received_cash=match_result.matched_notional,
            )
            ledger.release_asset(
                WHALE_AGENT_ID,
                ledger.get_balance(WHALE_AGENT_ID).asset_reserved,
            )

        book_after = self._build_order_book_snapshot(
            order_book,
            fallback_price=reference_price,
        )
        whale_balance = ledger.get_balance(WHALE_AGENT_ID)
        price_impact_bps = round(
            ((book_after.mid_price - book_before.mid_price) / book_before.mid_price) * 10_000,
            4,
        )

        notes = [
            f"Whale {side.value} preview executed against seeded liquidity.",
            f"Active compute backend resolved to {active_backend}.",
        ]
        if match_result.quantity_remaining > 1e-9:
            notes.append("Seeded book depth was exhausted before the full shock could fill.")

        return WhaleShockPreview(
            session_id=f"whale-{side.value}-{config.seed}-{config.agent_count}",
            config=config,
            shock=WhaleShockOutcome(
                side=side.value,
                requested_notional=round(notional, 6),
                requested_quantity=requested_quantity,
                matched_notional=match_result.matched_notional,
                matched_quantity=match_result.quantity_matched,
                quantity_remaining=match_result.quantity_remaining,
                average_fill_price=match_result.average_fill_price,
                trades_executed=match_result.trades_executed,
                price_impact_bps=price_impact_bps,
            ),
            order_book_before=book_before,
            order_book_after=book_after,
            whale_balance=WhaleBalanceSnapshot(
                cash_free=round(whale_balance.cash_free, 6),
                cash_reserved=round(whale_balance.cash_reserved, 6),
                asset_free=round(whale_balance.asset_free, 6),
                asset_reserved=round(whale_balance.asset_reserved, 6),
                initial_cash=whale_initial_cash,
                initial_asset=whale_initial_asset,
                initial_mark_price=reference_price,
                initial_total_equity=whale_initial_total_equity,
                total_equity=round(whale_balance.total_equity(book_after.mid_price), 6),
            ),
            notes=notes,
        )

    def _build_market_state(
        self,
        config: SessionConfig,
    ) -> tuple[str, list, Ledger, OrderBook]:
        try:
            active_backend = resolve_compute_backend(
                config.compute_mode,
                gpu_enabled=self.gpu_enabled,
            )
        except ComputeUnavailableError as exc:
            raise ValueError(str(exc)) from exc

        profiles = build_default_agent_profiles(
            config.agent_count,
            initial_cash=config.initial_cash,
            initial_asset=config.initial_asset,
        )
        ledger = Ledger.from_profiles(profiles)

        order_book = OrderBook()
        order_book.seed_around(config.initial_price, ttl_ticks=24)

        return active_backend, profiles, ledger, order_book

    def _build_order_book_snapshot(
        self,
        order_book: OrderBook,
        *,
        fallback_price: float,
    ) -> OrderBookSnapshot:
        best_bid = order_book.best_bid or fallback_price
        best_ask = order_book.best_ask or fallback_price
        mid_price = order_book.mid_price or fallback_price
        spread_bps = calculate_spread_bps(
            best_bid=best_bid,
            best_ask=best_ask,
            mid_price=mid_price,
        )

        bids, asks = order_book.snapshot(depth=10)

        return OrderBookSnapshot(
            best_bid=best_bid,
            best_ask=best_ask,
            mid_price=mid_price,
            spread_bps=spread_bps,
            bid_depth=order_book.bid_depth,
            ask_depth=order_book.ask_depth,
            bids=[OrderBookLevel(price=level.price, quantity=level.quantity, orders=level.orders) for level in bids],
            asks=[OrderBookLevel(price=level.price, quantity=level.quantity, orders=level.orders) for level in asks],
        )

    def _build_metrics(
        self,
        ledger: Ledger,
        order_book: OrderBook,
        active_backend: str,
        *,
        fallback_price: float,
    ) -> MarketMetrics:
        mark_price = order_book.mid_price or fallback_price
        total_asset_inventory = ledger.total_inventory()

        return MarketMetrics(
            market_cap=calculate_market_cap(
                mark_price=mark_price,
                total_asset_inventory=total_asset_inventory,
            ),
            average_agent_equity=round(ledger.average_equity(mark_price), 2),
            total_agent_equity=round(ledger.total_equity(mark_price), 2),
            total_asset_inventory=round(total_asset_inventory, 4),
            active_compute_backend=active_backend,
        )
