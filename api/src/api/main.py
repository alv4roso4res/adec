from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from api.config import Settings, get_settings
from api.errors import register_error_handlers
from api.routes import health

GITHUB_API_URL = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
        }
        # Sem token a API ainda responde (repos públicos, rate limit baixo);
        # "Bearer " vazio seria um header inválido.
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"

        async with httpx.AsyncClient(
            base_url=GITHUB_API_URL,
            headers=headers,
            timeout=10.0,
        ) as client:
            app.state.http_client = client
            yield

    app = FastAPI(
        title="api-adec",
        description="API desenvolvida com FastAPI",
        version=settings.app_version,
        lifespan=lifespan,
        # Tudo da API vive sob /api (é o que o nginx/proxy do Vite encaminham).
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.state.settings = settings

    register_error_handlers(app)
    app.include_router(health.router, prefix="/api")

    return app


app = create_app()
