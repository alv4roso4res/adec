"""Transforma runs/jobs crus do GitHub nas respostas dos cards 1 e 2.

Funções puras: não fazem requisição nem leem o relógio (`now` vem da rota) e
nunca alteram os dicts/listas recebidos — o cache do GitHubClient devolve o
mesmo objeto a cada chamada.
"""

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from api.schemas.common import RunStatus
from api.schemas.pipeline import (
    HistoryRun,
    HistoryStats,
    PipelineCurrent,
    PipelineHistory,
    PipelineJob,
    PipelineRun,
    PipelineStep,
)

Raw = Mapping[str, Any]

_QUEUED = {"queued", "waiting", "requested", "pending"}
_CONCLUSIONS = {
    "success": RunStatus.SUCCESS,
    "cancelled": RunStatus.CANCELLED,
    "skipped": RunStatus.SKIPPED,
    "neutral": RunStatus.SKIPPED,
}
_FINISHED = {
    RunStatus.SUCCESS,
    RunStatus.FAILURE,
    RunStatus.CANCELLED,
    RunStatus.SKIPPED,
}


def normalize_status(status: str | None, conclusion: str | None) -> RunStatus:
    """Junta `status` + `conclusion` do GitHub num RunStatus nosso."""
    if status in _QUEUED:
        return RunStatus.QUEUED
    if status == "in_progress":
        return RunStatus.IN_PROGRESS
    # completed: failure, timed_out, action_required, startup_failure, stale
    # ou qualquer conclusão desconhecida contam como falha.
    return _CONCLUSIONS.get(conclusion or "", RunStatus.FAILURE)


def duration_seconds(
    status: RunStatus,
    started_at: str | None,
    finished_at: str | None,
    now: datetime,
) -> int | None:
    """Segundos de `started_at` até o fim (concluído) ou até `now` (rodando).

    None quando ainda está na fila ou falta alguma data. Nunca negativo.
    """
    start = _parse_dt(started_at)
    if status is RunStatus.QUEUED or start is None:
        return None
    if status is RunStatus.IN_PROGRESS:
        end = now
    else:
        end = _parse_dt(finished_at)
        if end is None:
            return None
    return max(0, int((end - start).total_seconds()))


def build_current(
    runs: Sequence[Raw],
    jobs: Sequence[Raw],
    now: datetime,
) -> PipelineCurrent:
    if not runs:
        return PipelineCurrent(run=None, jobs=[])
    return PipelineCurrent(
        run=_to_run(runs[0], now),
        jobs=[_to_job(job, now) for job in jobs],
    )


def build_history(runs: Sequence[Raw], now: datetime) -> PipelineHistory:
    items = [_to_history_run(run, now) for run in runs]
    return PipelineHistory(runs=items, stats=_stats(items))


# ------------------------------------------------------------------ internos


def _run_status(raw: Raw) -> RunStatus:
    return normalize_status(raw.get("status"), raw.get("conclusion"))


def _run_duration(raw: Raw, status: RunStatus, now: datetime) -> int | None:
    return duration_seconds(
        status, raw.get("run_started_at"), raw.get("updated_at"), now
    )


def _to_run(raw: Raw, now: datetime) -> PipelineRun:
    status = _run_status(raw)
    message = (raw.get("head_commit") or {}).get("message") or ""
    return PipelineRun(
        id=raw["id"],
        status=status,
        event=raw["event"],
        branch=raw.get("head_branch") or "",
        head_sha=raw["head_sha"],
        commit_message=message.splitlines()[0] if message else "",
        actor=(raw.get("actor") or {}).get("login") or "",
        started_at=raw.get("run_started_at"),
        duration_seconds=_run_duration(raw, status, now),
        html_url=raw["html_url"],
    )


def _to_job(raw: Raw, now: datetime) -> PipelineJob:
    status = _run_status(raw)
    return PipelineJob(
        name=raw["name"],
        status=status,
        duration_seconds=duration_seconds(
            status, raw.get("started_at"), raw.get("completed_at"), now
        ),
        steps=[
            PipelineStep(
                name=step["name"],
                status=_run_status(step),
                number=step["number"],
            )
            for step in raw.get("steps") or []
        ],
    )


def _to_history_run(raw: Raw, now: datetime) -> HistoryRun:
    status = _run_status(raw)
    return HistoryRun(
        id=raw["id"],
        status=status,
        event=raw["event"],
        branch=raw.get("head_branch") or "",
        head_sha=raw["head_sha"],
        duration_seconds=_run_duration(raw, status, now),
        created_at=raw["created_at"],
    )


def _stats(runs: list[HistoryRun]) -> HistoryStats:
    successes = sum(r.status is RunStatus.SUCCESS for r in runs)
    failures = sum(r.status is RunStatus.FAILURE for r in runs)
    decided = successes + failures
    durations = [
        r.duration_seconds
        for r in runs
        if r.status in _FINISHED and r.duration_seconds is not None
    ]
    return HistoryStats(
        total=len(runs),
        success_rate=round(successes / decided, 3) if decided else None,
        avg_duration_seconds=(
            round(sum(durations) / len(durations)) if durations else None
        ),
        # O deploy só roda em push na main, e o run só fica verde se ele passar.
        deploys=sum(
            r.event == "push" and r.branch == "main" and r.status is RunStatus.SUCCESS
            for r in runs
        ),
        by_event=dict(Counter(r.event for r in runs)),
    )


def _parse_dt(value: str | None) -> datetime | None:
    # O GitHub manda ISO 8601 com "Z"; fromisoformat entende desde o 3.11.
    return datetime.fromisoformat(value) if value else None
