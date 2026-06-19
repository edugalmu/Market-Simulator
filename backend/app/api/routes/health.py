from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config.settings import Settings, get_settings


router = APIRouter()


class HealthResponse(BaseModel):
    name: str
    version: str
    phase: str
    compute_modes: list[str]
    default_compute_mode: str
    gpu_enabled: bool
    docs: list[str]


@router.get("/health", response_model=HealthResponse)
def read_health(
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    return HealthResponse(
        name=settings.app_name,
        version=settings.app_version,
        phase="scaffold",
        compute_modes=["cpu", "gpu_auto", "gpu_force"],
        default_compute_mode=settings.default_compute_mode,
        gpu_enabled=settings.gpu_enabled,
        docs=[
            "/docs",
            f"{settings.api_prefix}/simulation/defaults",
            f"{settings.api_prefix}/simulation/bootstrap",
        ],
    )
