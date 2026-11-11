from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from api.config import Settings, get_settings
from api.errors import register_error_handlers
from api.github.cache import ResponseCache
from api.github.client import GitHubClient
from api.routes import commits, health, pipeline, pulls, team, version

GITHUB_API_URL = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"

APP_TITLE = "ADEC — API do painel de CI/CD"

APP_DESCRIPTION = """
Backend do painel de uma tela que mostra o **pipeline do próprio repositório**
(runs, PRs, commits, versão publicada e equipe). O frontend nunca fala com o
GitHub direto: consulta a API do GitHub **através desta API**.

**Convenções**

- Todas as rotas ficam sob `/api`.
- JSON em **camelCase**; datas em **ISO 8601 UTC** (ex.: `2026-11-11T00:57:48Z`).
- Respostas do GitHub ficam em cache por poucos segundos (TTL + ETag), então os
  dados podem estar alguns segundos atrasados.
- Todo erro tem o formato `{"detail": "..."}`.

**Status de erro**

| Status | Quando |
|---|---|
| 502 | Falha ao falar com o GitHub (rede, timeout, 5xx) ou token inválido/sem permissão |
| 503 | Rate limit do GitHub esgotado |
| 409 | Merge recusado pelo GitHub (PR bloqueado ou com conflito) |
| 403 | Ações de escrita desligadas (`ENABLE_WRITE_ACTIONS=false`) |
| 422 | Parâmetro inválido (ou pedido recusado pelo GitHub) |
"""

# Descrição de cada tag (inclusive as das próximas etapas, para o Swagger já
# mostrar a organização final). Toda tag usada precisa estar aqui.
OPENAPI_TAGS = [
    {"name": "health", "description": "Saúde da API e versão em execução."},
    {
        "name": "pipeline",
        "description": "Cards 1 e 2: status atual da main e últimos runs do workflow.",
    },
    {
        "name": "commits",
        "description": "Card 6: últimos commits da main com o status do pipeline.",
    },
    {
        "name": "version",
        "description": "Card 5: versão rodando × versão publicada no GHCR.",
    },
    {
        "name": "team",
        "description": "Card 4: integrantes do time, PRs e commits de cada um.",
    },
    {
        "name": "pulls",
        "description": "Card 3: PRs abertos, badges de estado, aprovar e mergear.",
    },
]

SWAGGER_UI_PARAMETERS = {
    "displayRequestDuration": True,
    "tryItOutEnabled": True,
    "defaultModelsExpandDepth": 1,
}


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
            # Um cache por app: vive enquanto o processo estiver de pé.
            app.state.github_client = GitHubClient(client, settings, ResponseCache())
            yield

    app = FastAPI(
        title=APP_TITLE,
        description=APP_DESCRIPTION,
        version=settings.app_version,
        openapi_tags=OPENAPI_TAGS,
        swagger_ui_parameters=SWAGGER_UI_PARAMETERS,
        lifespan=lifespan,
        # Tudo da API vive sob /api (é o que o nginx/proxy do Vite encaminham).
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.state.settings = settings

    register_error_handlers(app)
    app.include_router(health.router, prefix="/api")
    app.include_router(pipeline.router, prefix="/api")
    app.include_router(commits.router, prefix="/api")
    app.include_router(version.router, prefix="/api")
    app.include_router(team.router, prefix="/api")
    app.include_router(pulls.router, prefix="/api")

    return app


app = create_app()
