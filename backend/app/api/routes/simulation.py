from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.events import OrderSide
from app.config.settings import Settings, get_settings
from app.simulation.engine import SimulationEngine
from app.simulation.live import get_live_simulation_service
from app.simulation.models import (
    LiveSimulationSnapshot,
    LiveWhaleOrderRequest,
    LiveWhaleOrderResponse,
    SessionConfig,
    SimulationSummary,
    WhaleShockPreview,
)


router = APIRouter(prefix="/simulation")


@router.get("/defaults", response_model=SessionConfig)
def read_defaults(
    settings: Annotated[Settings, Depends(get_settings)],
) -> SessionConfig:
    return SessionConfig(compute_mode=settings.default_compute_mode)


@router.get("/bootstrap", response_model=SimulationSummary)
def bootstrap_simulation(
    settings: Annotated[Settings, Depends(get_settings)],
    seed: int = Query(default=7, ge=1),
    agent_count: int = Query(default=1000, ge=100, le=5000),
    initial_price: float = Query(default=100.0, gt=0),
    initial_cash: float = Query(default=50000.0, gt=0),
    initial_asset: float = Query(default=1.25, ge=0),
    compute_mode: Literal["cpu", "gpu_auto", "gpu_force"] = Query(
        default="cpu"
    ),
) -> SimulationSummary:
    engine = SimulationEngine(gpu_enabled=settings.gpu_enabled)
    config = SessionConfig(
        seed=seed,
        agent_count=agent_count,
        initial_price=initial_price,
        initial_cash=initial_cash,
        initial_asset=initial_asset,
        compute_mode=compute_mode,
    )

    try:
        return engine.bootstrap_session(config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/whale-shock/preview", response_model=WhaleShockPreview)
def preview_whale_shock(
    settings: Annotated[Settings, Depends(get_settings)],
    side: Literal["buy", "sell"] = Query(default="sell"),
    notional: float = Query(default=1_000.0, gt=0),
    seed: int = Query(default=7, ge=1),
    agent_count: int = Query(default=1000, ge=100, le=5000),
    initial_price: float = Query(default=100.0, gt=0),
    initial_cash: float = Query(default=50000.0, gt=0),
    initial_asset: float = Query(default=1.25, ge=0),
    compute_mode: Literal["cpu", "gpu_auto", "gpu_force"] = Query(
        default="cpu"
    ),
) -> WhaleShockPreview:
    engine = SimulationEngine(gpu_enabled=settings.gpu_enabled)
    config = SessionConfig(
        seed=seed,
        agent_count=agent_count,
        initial_price=initial_price,
        initial_cash=initial_cash,
        initial_asset=initial_asset,
        compute_mode=compute_mode,
    )

    try:
        return engine.preview_whale_shock(
            config,
            side=OrderSide(side),
            notional=notional,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/live/start", response_model=LiveSimulationSnapshot)
def start_live_simulation(
    settings: Annotated[Settings, Depends(get_settings)],
    live_service=Depends(get_live_simulation_service),
    seed: int = Query(default=7, ge=1),
    agent_count: int = Query(default=1000, ge=100, le=5000),
    initial_price: float = Query(default=100.0, gt=0),
    initial_cash: float = Query(default=50000.0, gt=0),
    initial_asset: float = Query(default=1.25, ge=0),
    tick_interval_ms: int = Query(default=750, ge=100, le=5000),
    compute_mode: Literal["cpu", "gpu_auto", "gpu_force"] = Query(
        default="cpu"
    ),
) -> LiveSimulationSnapshot:
    config = SessionConfig(
        seed=seed,
        agent_count=agent_count,
        initial_price=initial_price,
        initial_cash=initial_cash,
        initial_asset=initial_asset,
        compute_mode=compute_mode,
    )

    try:
        return live_service.start(
            config,
            gpu_enabled=settings.gpu_enabled,
            tick_interval_ms=tick_interval_ms,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/live/play", response_model=LiveSimulationSnapshot)
def play_live_simulation(
    live_service=Depends(get_live_simulation_service),
    tick_interval_ms: int | None = Query(default=None, ge=100, le=5000),
) -> LiveSimulationSnapshot:
    try:
        return live_service.play(tick_interval_ms=tick_interval_ms)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/live/game/start", response_model=LiveSimulationSnapshot)
def start_live_game(
    live_service=Depends(get_live_simulation_service),
    mode: Literal["whale_challenge"] = Query(default="whale_challenge"),
    duration_ticks: int = Query(default=60, ge=10, le=600),
) -> LiveSimulationSnapshot:
    try:
        return live_service.start_game(mode=mode, duration_ticks=duration_ticks)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/live/game/end", response_model=LiveSimulationSnapshot)
def end_live_game(
    live_service=Depends(get_live_simulation_service),
) -> LiveSimulationSnapshot:
    try:
        return live_service.end_game()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/live/game/reset", response_model=LiveSimulationSnapshot)
def reset_live_game(
    live_service=Depends(get_live_simulation_service),
) -> LiveSimulationSnapshot:
    try:
        return live_service.reset_game()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/live", response_model=LiveSimulationSnapshot)
def read_live_simulation(
    live_service=Depends(get_live_simulation_service),
) -> LiveSimulationSnapshot:
    snapshot = live_service.get_snapshot()
    if snapshot is None:
        raise HTTPException(status_code=404, detail="No live simulation session is active.")

    return snapshot


@router.post("/live/step", response_model=LiveSimulationSnapshot)
def step_live_simulation(
    live_service=Depends(get_live_simulation_service),
    ticks: int = Query(default=1, ge=1, le=120),
) -> LiveSimulationSnapshot:
    try:
        return live_service.step(ticks=ticks)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/live/stop", response_model=LiveSimulationSnapshot)
def stop_live_simulation(
    live_service=Depends(get_live_simulation_service),
) -> LiveSimulationSnapshot:
    try:
        return live_service.stop()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/live/whale-order", response_model=LiveWhaleOrderResponse)
def execute_live_whale_order(
    payload: LiveWhaleOrderRequest,
    live_service=Depends(get_live_simulation_service),
) -> LiveWhaleOrderResponse:
    try:
        return live_service.execute_whale_order(
            side=payload.side,
            notional=payload.notional,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
