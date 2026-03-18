from fastapi import FastAPI

from spatial_data_api.api.routes import router
from spatial_data_api.core.config import get_settings


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    summary="A small geospatial backend starter built with FastAPI.",
)
app.include_router(router)


@app.get("/", tags=["root"])
def read_root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "api_prefix": settings.api_prefix,
    }