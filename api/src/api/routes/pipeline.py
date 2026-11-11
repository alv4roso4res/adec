from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from api.config import Settings
from api.deps import get_github_client, get_settings
from api.github.client import GitHubClient
from api.schemas.pipeline import PipelineCurrent, PipelineHistory
from api.services.pipeline import build_current, build_history

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

Client = Annotated[GitHubClient, Depends(get_github_client)]


@router.get("/current", response_model=PipelineCurrent)
async def current(github: Client) -> PipelineCurrent:
    """Card 1: último run do workflow em push na main e os jobs dele."""
    runs = await github.list_workflow_runs(branch="main", event="push", limit=1)
    jobs = await github.list_run_jobs(runs[0]["id"]) if runs else []
    return build_current(runs, jobs, now=datetime.now(UTC))


@router.get("/history", response_model=PipelineHistory)
async def history(
    github: Client,
    settings: Annotated[Settings, Depends(get_settings)],
    # Sem valor: usa HISTORY_LIMIT (o padrão vem das settings, não do import).
    limit: Annotated[int | None, Query(ge=1, le=100)] = None,
) -> PipelineHistory:
    """Card 2: últimos runs do workflow, de todos os eventos e branches."""
    runs = await github.list_workflow_runs(limit=limit or settings.history_limit)
    return build_history(runs, now=datetime.now(UTC))
