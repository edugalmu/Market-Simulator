from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.config.settings import get_settings


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    summary="Local-first API scaffold for the market simulator.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_dev_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)

if settings.frontend_dist_dir.exists():
    assets_dir = settings.frontend_dist_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


def _index_file() -> FileResponse:
    return FileResponse(settings.frontend_dist_dir / "index.html")


@app.get("/", tags=["root"])
def read_root() -> dict[str, object]:
    if settings.frontend_dist_dir.exists():
        return _index_file()

    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "phase": "scaffold",
        "docs": ["/docs", f"{settings.api_prefix}/health"],
        "notes": [
            "Simulation engine and UI are intentionally separated.",
            "GPU support is optional and currently resolves through config only.",
        ],
    }


@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str):
    if not settings.frontend_dist_dir.exists():
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "phase": "scaffold",
            "docs": ["/docs", f"{settings.api_prefix}/health"],
            "missing": full_path,
        }

    requested_file = settings.frontend_dist_dir / full_path
    if full_path and requested_file.exists() and requested_file.is_file():
        return FileResponse(requested_file)

    return _index_file()
