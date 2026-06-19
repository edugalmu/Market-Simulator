from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _as_bool(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True, frozen=True)
class Settings:
    app_name: str
    app_version: str
    api_prefix: str
    frontend_dev_url: str
    frontend_dist_dir: Path
    default_compute_mode: str
    gpu_enabled: bool


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("MARKET_SIMULATOR_APP_NAME", "Market Simulator API"),
        app_version=os.getenv("MARKET_SIMULATOR_APP_VERSION", "0.1.0"),
        api_prefix="/api/v1",
        frontend_dev_url=os.getenv(
            "MARKET_SIMULATOR_FRONTEND_DEV_URL", "http://127.0.0.1:5173"
        ),
        frontend_dist_dir=Path(
            os.getenv(
                "MARKET_SIMULATOR_FRONTEND_DIST_DIR",
                str(Path(__file__).resolve().parents[3] / "frontend" / "dist"),
            )
        ),
        default_compute_mode=os.getenv(
            "MARKET_SIMULATOR_DEFAULT_COMPUTE_MODE", "cpu"
        ),
        gpu_enabled=_as_bool(os.getenv("MARKET_SIMULATOR_GPU_ENABLED")),
    )
