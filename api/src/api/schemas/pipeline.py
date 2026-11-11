"""Respostas dos cards 1 (status da main) e 2 (últimos runs).

Os exemplos vêm das fixtures reais em tests/fixtures/github/ (run 42935390858,
push na main).
"""

from datetime import datetime

from pydantic import ConfigDict, Field

from api.schemas.common import ApiModel, RunStatus

# ----------------------------------------------------------- exemplos

_SHA = "5ef37333051d1315423f73b75dec0ad76182796d"
_RUN_URL = "https://github.com/alv4roso4res/adec/actions/runs/42935390858"

_STEP_EXAMPLE = {"name": "API - rodar os testes (pytest)", "status": "success", "number": 5}
_JOB_EXAMPLE = {
    "name": "build-test",
    "status": "success",
    "durationSeconds": 81,
    "steps": [
        {"name": "Set up job", "status": "success", "number": 1},
        _STEP_EXAMPLE,
    ],
}
_DEPLOY_EXAMPLE = {
    "name": "deploy",
    "status": "success",
    "durationSeconds": 32,
    "steps": [
        {"name": "Publicar a imagem da API (tag sha)", "status": "success", "number": 6},
        {"name": "Promover a tag latest (API e frontend)", "status": "success", "number": 8},
    ],
}
_RUN_EXAMPLE = {
    "id": 42935390858,
    "status": "success",
    "event": "push",
    "branch": "main",
    "headSha": _SHA,
    "commitMessage": "Merge pull request #6 from alv4roso4res/feat/frontend-fundo-css",
    "actor": "alv4roso4res",
    "startedAt": "2026-11-11T00:57:48Z",
    "durationSeconds": 118,
    "htmlUrl": _RUN_URL,
}
_HISTORY_RUN_EXAMPLE = {
    "id": 42935390858,
    "status": "success",
    "event": "push",
    "branch": "main",
    "headSha": _SHA,
    "durationSeconds": 118,
    "createdAt": "2026-11-11T00:57:48Z",
}
_HISTORY_PR_EXAMPLE = {
    "id": 42931682530,
    "status": "success",
    "event": "pull_request",
    "branch": "feat/frontend-fundo-css",
    "headSha": "4ed40c4980571aaf3ce11326aa93b591e5a96747",
    "durationSeconds": 84,
    "createdAt": "2026-11-11T00:28:56Z",
}
_STATS_EXAMPLE = {
    "total": 10,
    "successRate": 1.0,
    "avgDurationSeconds": 116,
    "deploys": 5,
    "byEvent": {"push": 5, "pull_request": 5},
}

# ------------------------------------------------------------ campos comuns


def _status_field() -> object:
    return Field(
        description="Status normalizado (ver o schema RunStatus).",
        examples=["success"],
    )


def _duration_field(what: str) -> object:
    return Field(
        description=(
            f"Duração {what} em segundos: até o fim quando concluído, até agora "
            "quando em andamento; null na fila ou sem data de início."
        ),
        examples=[118],
    )


# ----------------------------------------------------------------- modelos


class PipelineStep(ApiModel):
    """Um step de um job do workflow."""

    name: str = Field(
        description="Nome do step, como está no ci.yml.",
        examples=["API - rodar os testes (pytest)"],
    )
    status: RunStatus = _status_field()
    number: int = Field(
        description="Posição do step dentro do job (começa em 1).",
        examples=[5],
    )


class PipelineJob(ApiModel):
    """Um job do run (build-test ou deploy) com seus steps."""

    name: str = Field(
        description="Nome do job no workflow.",
        examples=["build-test", "deploy"],
    )
    status: RunStatus = _status_field()
    duration_seconds: int | None = _duration_field("do job")
    steps: list[PipelineStep] = Field(
        description="Steps do job, na ordem de execução.",
        examples=[_JOB_EXAMPLE["steps"]],
    )


class PipelineRun(ApiModel):
    """Um run do workflow de CI/CD, com os dados do commit que o disparou."""

    id: int = Field(description="ID do run no GitHub Actions.", examples=[42935390858])
    status: RunStatus = _status_field()
    event: str = Field(
        description="Evento que disparou o run.",
        examples=["push", "pull_request"],
    )
    branch: str = Field(description="Branch do run.", examples=["main"])
    head_sha: str = Field(description="SHA completo do commit.", examples=[_SHA])
    commit_message: str = Field(
        description="Primeira linha da mensagem do commit.",
        examples=[_RUN_EXAMPLE["commitMessage"]],
    )
    actor: str = Field(
        description="Login de quem disparou o run.",
        examples=["alv4roso4res"],
    )
    started_at: datetime | None = Field(
        description="Início do run (ISO 8601 UTC); null se ainda não começou.",
        examples=["2026-11-11T00:57:48Z"],
    )
    duration_seconds: int | None = _duration_field("do run")
    html_url: str = Field(description="Link do run no GitHub.", examples=[_RUN_URL])


class PipelineCurrent(ApiModel):
    """Card 1: último run em push na main e os jobs dele."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"run": _RUN_EXAMPLE, "jobs": [_JOB_EXAMPLE, _DEPLOY_EXAMPLE]}]
        }
    )

    run: PipelineRun | None = Field(
        description="Último run em push na main; null quando ainda não há runs.",
        examples=[_RUN_EXAMPLE],
    )
    jobs: list[PipelineJob] = Field(
        description="Jobs do run (vazio quando run é null).",
        examples=[[_JOB_EXAMPLE, _DEPLOY_EXAMPLE]],
    )


class HistoryRun(ApiModel):
    """Um item da lista de últimos runs (versão resumida de PipelineRun)."""

    id: int = Field(description="ID do run no GitHub Actions.", examples=[42935390858])
    status: RunStatus = _status_field()
    event: str = Field(
        description="Evento que disparou o run.",
        examples=["push", "pull_request"],
    )
    branch: str = Field(
        description="Branch do run.",
        examples=["main", "feat/frontend-fundo-css"],
    )
    head_sha: str = Field(description="SHA completo do commit.", examples=[_SHA])
    duration_seconds: int | None = _duration_field("do run")
    created_at: datetime = Field(
        description="Quando o run foi criado (ISO 8601 UTC).",
        examples=["2026-11-11T00:57:48Z"],
    )


class HistoryStats(ApiModel):
    """Estatísticas calculadas sobre os runs devolvidos em `runs`."""

    total: int = Field(description="Quantidade de runs na lista.", examples=[10])
    success_rate: float | None = Field(
        description=(
            "Sucessos / (sucessos + falhas), de 0 a 1 com 3 casas. Cancelados, "
            "skipped e não concluídos ficam fora; null se não houver nenhum."
        ),
        examples=[0.667],
    )
    avg_duration_seconds: int | None = Field(
        description="Média de duração só dos runs concluídos; null se não houver.",
        examples=[116],
    )
    deploys: int = Field(
        description="Runs em push na main com sucesso (o deploy só roda nesse caso).",
        examples=[5],
    )
    by_event: dict[str, int] = Field(
        description="Quantidade de runs por evento.",
        examples=[{"push": 5, "pull_request": 5}],
    )


class PipelineHistory(ApiModel):
    """Card 2: últimos runs do workflow (todos os eventos e branches) e stats."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "runs": [_HISTORY_RUN_EXAMPLE, _HISTORY_PR_EXAMPLE],
                    "stats": _STATS_EXAMPLE,
                }
            ]
        }
    )

    runs: list[HistoryRun] = Field(
        description="Runs do mais recente para o mais antigo.",
        examples=[[_HISTORY_RUN_EXAMPLE, _HISTORY_PR_EXAMPLE]],
    )
    stats: HistoryStats = Field(
        description="Estatísticas sobre a lista `runs`.",
        examples=[_STATS_EXAMPLE],
    )
