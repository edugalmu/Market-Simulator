from __future__ import annotations

from dataclasses import dataclass

from app.agents.base import AgentProfile


@dataclass(slots=True)
class AgentBalance:
    cash_free: float
    cash_reserved: float
    asset_free: float
    asset_reserved: float

    def total_equity(self, mark_price: float) -> float:
        return self.cash_free + self.cash_reserved + (
            self.asset_free + self.asset_reserved
        ) * mark_price


class Ledger:
    def __init__(self, balances: dict[int, AgentBalance]) -> None:
        self._balances = balances

    @classmethod
    def from_profiles(cls, profiles: list[AgentProfile]) -> "Ledger":
        return cls(
            {
                profile.agent_id: AgentBalance(
                    cash_free=profile.initial_cash,
                    cash_reserved=0.0,
                    asset_free=profile.initial_asset,
                    asset_reserved=0.0,
                )
                for profile in profiles
            }
        )

    def reserve_cash(self, agent_id: int, amount: float) -> None:
        balance = self._balances[agent_id]
        if amount > balance.cash_free:
            raise ValueError("Insufficient free cash for reservation.")
        balance.cash_free -= amount
        balance.cash_reserved += amount

    def reserve_asset(self, agent_id: int, quantity: float) -> None:
        balance = self._balances[agent_id]
        if quantity > balance.asset_free:
            raise ValueError("Insufficient free asset for reservation.")
        balance.asset_free -= quantity
        balance.asset_reserved += quantity

    def release_cash(self, agent_id: int, amount: float) -> None:
        balance = self._balances[agent_id]
        released = min(amount, balance.cash_reserved)
        balance.cash_reserved -= released
        balance.cash_free += released

    def release_asset(self, agent_id: int, quantity: float) -> None:
        balance = self._balances[agent_id]
        released = min(quantity, balance.asset_reserved)
        balance.asset_reserved -= released
        balance.asset_free += released

    def add_balance(
        self,
        agent_id: int,
        *,
        cash_free: float,
        asset_free: float,
    ) -> None:
        self._balances[agent_id] = AgentBalance(
            cash_free=cash_free,
            cash_reserved=0.0,
            asset_free=asset_free,
            asset_reserved=0.0,
        )

    def apply_buy_fill(
        self,
        agent_id: int,
        *,
        spent_cash: float,
        received_asset: float,
    ) -> None:
        balance = self._balances[agent_id]
        if spent_cash > balance.cash_reserved + 1e-9:
            raise ValueError("Buy fill exceeds reserved cash.")
        balance.cash_reserved = max(balance.cash_reserved - spent_cash, 0.0)
        balance.asset_free += received_asset

    def apply_sell_fill(
        self,
        agent_id: int,
        *,
        sold_asset: float,
        received_cash: float,
    ) -> None:
        balance = self._balances[agent_id]
        if sold_asset > balance.asset_reserved + 1e-9:
            raise ValueError("Sell fill exceeds reserved asset.")
        balance.asset_reserved = max(balance.asset_reserved - sold_asset, 0.0)
        balance.cash_free += received_cash

    def get_balance(self, agent_id: int) -> AgentBalance:
        return self._balances[agent_id]

    def average_equity(self, mark_price: float) -> float:
        total = sum(balance.total_equity(mark_price) for balance in self._balances.values())
        return total / len(self._balances)

    def total_inventory(self) -> float:
        return sum(
            balance.asset_free + balance.asset_reserved
            for balance in self._balances.values()
        )
