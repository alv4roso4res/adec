from typing import Annotated

from fastapi import APIRouter, Depends, Query

from api.config import Settings
from api.deps import get_github_client, get_settings
from api.errors import GITHUB_ERROR_RESPONSES
from api.github.client import GitHubClient
from api.routes.pipeline import fetch_history_runs
from api.schemas.commits import CommitItem
from api.services.commits import build_commits

router = APIRouter(prefix="/commits", tags=["commits"])

DEFAULT_LIMIT = 8


@router.get(
    "",
    response_model=list[CommitItem],
    responses=GITHUB_ERROR_RESPONSES,
    operation_id="get_commits",
    summary="Últimos commits da main",
    description=(
        "**Card 6 (commits da main).** Últimos commits da `main`, do mais novo "
        "para o mais antigo, cada um com o status do pipeline que rodou nele "
        "(o run mais recente do SHA, preferindo push a pull_request). Dados de "
        "`GET /commits?sha=main` do GitHub (cache de 15 s); o status vem dos "
        "mesmos runs do card 2 (`/api/pipeline/history` sem `limit`), já em "
        "cache, sem requisição extra.\n\n"
        "`pipelineStatus` é null quando o commit não aparece nesses runs "
        "recentes."
    ),
    response_description="Commits da main com o status do pipeline de cada um.",
)
async def commits(
    github: Annotated[GitHubClient, Depends(get_github_client)],
    settings: Annotated[Settings, Depends(get_settings)],
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=30,
            description=f"Quantos commits trazer, de 1 a 30 (padrão {DEFAULT_LIMIT}).",
            examples=[DEFAULT_LIMIT],
        ),
    ] = DEFAULT_LIMIT,
) -> list[CommitItem]:
    commits = await github.list_commits(branch="main", limit=limit)
    runs = await fetch_history_runs(github, settings)
    return build_commits(commits, runs)
