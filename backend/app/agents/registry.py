from __future__ import annotations

from collections.abc import Iterable

from app.agents.base import AgentProfile, StrategyType


DEFAULT_AGENT_MIX: tuple[tuple[StrategyType, float], ...] = (
    (StrategyType.NOISE, 0.45),
    (StrategyType.MOMENTUM, 0.20),
    (StrategyType.MEAN_REVERSION, 0.15),
    (StrategyType.MARKET_MAKER, 0.12),
    (StrategyType.FUNDAMENTAL, 0.08),
)


def _allocate_counts(total_agents: int) -> list[tuple[StrategyType, int]]:
    counts = [int(total_agents * ratio) for _, ratio in DEFAULT_AGENT_MIX]
    remainder = total_agents - sum(counts)

    for index in range(remainder):
        counts[index % len(counts)] += 1

    return [
        (strategy, count)
        for (strategy, _), count in zip(DEFAULT_AGENT_MIX, counts, strict=True)
    ]


def build_default_agent_profiles(
    total_agents: int,
    *,
    initial_cash: float,
    initial_asset: float,
) -> list[AgentProfile]:
    profiles: list[AgentProfile] = []
    next_agent_id = 1

    for strategy, count in _allocate_counts(total_agents):
        profiles.extend(
            AgentProfile(
                agent_id=agent_id,
                strategy=strategy,
                initial_cash=initial_cash,
                initial_asset=initial_asset,
            )
            for agent_id in range(next_agent_id, next_agent_id + count)
        )
        next_agent_id += count

    return profiles


def summarize_agent_mix(profiles: Iterable[AgentProfile]) -> dict[str, int]:
    mix: dict[str, int] = {}
    for profile in profiles:
        key = profile.strategy.value
        mix[key] = mix.get(key, 0) + 1
    return mix
