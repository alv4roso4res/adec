from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from api.config import Settings
from api.deps import get_github_client, get_settings
from api.errors import GITHUB_ERROR_RESPONSES
from api.github.client import GitHubClient
from api.schemas.pipeline import PipelineCurrent, PipelineHistory
from api.services.pipeline import build_current, build_history

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

Client = Annotated[GitHubClient, Depends(get_github_client)]


async def fetch_history_runs(
    github: GitHubClient,
    settings: Settings,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Runs do card 2. O card 6 (/api/commits) usa esta MESMA chamada, sem
    `limit`: argumentos iguais caem na mesma chave do cache do GitHubClient e
    o cruzamento commit × run não gasta requisição extra."""
    return await github.list_workflow_runs(limit=limit or settings.history_limit)


@router.get(
    "/current",
    response_model=PipelineCurrent,
    responses=GITHUB_ERROR_RESPONSES,
    operation_id="get_pipeline_current",
    summary="Status atual da main",
    description=(
        "**Card 1 (status da main).** Último run do workflow de CI/CD disparado "
        "por push na `main`, com os jobs (`build-test` e `deploy`) e os steps "
        "de cada um. Dados de `GET /actions/workflows/{arquivo}/runs` e "
        "`GET /actions/runs/{id}/jobs` do GitHub, em cache por 5 s.\n\n"
        "Retorna `run: null` e `jobs: []` quando ainda não há runs."
    ),
    response_description="Último run da main e seus jobs (ou run null).",
)
async def current(github: Client) -> PipelineCurrent:
    runs = await github.list_workflow_runs(branch="main", event="push", limit=1)
    jobs = await github.list_run_jobs(runs[0]["id"]) if runs else []
    return build_current(runs, jobs, now=datetime.now(UTC))


@router.get(
    "/history",
    response_model=PipelineHistory,
    responses=GITHUB_ERROR_RESPONSES,
    operation_id="get_pipeline_history",
    summary="Últimos runs e estatísticas",
    description=(
        "**Card 2 (últimos runs).** Últimos runs do workflow de CI/CD, de todos "
        "os eventos e branches, do mais recente para o mais antigo, com "
        "estatísticas: taxa de sucesso (sem cancelados), duração média (só "
        "concluídos), quantidade de deploys e contagem por evento. Dados de "
        "`GET /actions/workflows/{arquivo}/runs` do GitHub, em cache por 5 s."
    ),
    response_description="Lista de runs e estatísticas sobre ela.",
)
async def history(
    github: Client,
    settings: Annotated[Settings, Depends(get_settings)],
    # Sem valor: usa HISTORY_LIMIT (o padrão vem das settings, não do import).
    limit: Annotated[
        int | None,
        Query(
            ge=1,
            le=100,
            description=(
                "Quantos runs trazer, de 1 a 100. Sem valor, usa HISTORY_LIMIT "
                "(padrão 20)."
            ),
            examples=[20],
        ),
    ] = None,
) -> PipelineHistory:
    runs = await fetch_history_runs(github, settings, limit)
    return build_history(runs, now=datetime.now(UTC))
