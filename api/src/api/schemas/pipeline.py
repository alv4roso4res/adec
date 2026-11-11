"""Respostas dos cards 1 (status da main) e 2 (últimos runs)."""

from datetime import datetime

from api.schemas.common import ApiModel, RunStatus


class PipelineStep(ApiModel):
    name: str
    status: RunStatus
    number: int


class PipelineJob(ApiModel):
    name: str
    status: RunStatus
    duration_seconds: int | None
    steps: list[PipelineStep]


class PipelineRun(ApiModel):
    id: int
    status: RunStatus
    event: str
    branch: str
    head_sha: str
    commit_message: str
    actor: str
    started_at: datetime | None
    duration_seconds: int | None
    html_url: str


class PipelineCurrent(ApiModel):
    run: PipelineRun | None
    jobs: list[PipelineJob]


class HistoryRun(ApiModel):
    id: int
    status: RunStatus
    event: str
    branch: str
    head_sha: str
    duration_seconds: int | None
    created_at: datetime


class HistoryStats(ApiModel):
    total: int
    # De 0 a 1 (3 casas); None quando não há run concluído com sucesso/falha.
    success_rate: float | None
    avg_duration_seconds: int | None
    deploys: int
    by_event: dict[str, int]


class PipelineHistory(ApiModel):
    runs: list[HistoryRun]
    stats: HistoryStats
