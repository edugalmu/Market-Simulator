def select_active_agent_count(total_agents: int, *, activation_ratio: float = 0.15) -> int:
    return max(1, int(total_agents * activation_ratio))
