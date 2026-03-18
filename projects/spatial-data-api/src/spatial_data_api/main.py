from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from spatial_data_api.api.routes import router
from spatial_data_api.core.config import get_settings


settings = get_settings()
dashboard_dir = Path(__file__).resolve().parent / "dashboard"

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    summary="An environmental monitoring backend with geospatial and analytics-friendly APIs.",
)
app.include_router(router)
app.mount("/dashboard/assets", StaticFiles(directory=dashboard_dir), name="dashboard-assets")


@app.get("/", tags=["root"])
def read_root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "dashboard": "/dashboard",
        "api_prefix": settings.api_prefix,
    }


@app.get("/dashboard", include_in_schema=False)
def read_dashboard() -> FileResponse:
    return FileResponse(dashboard_dir / "index.html")