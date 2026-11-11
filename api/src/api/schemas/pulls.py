"""Resposta do card 3 (PRs abertos com badge de estado).

Os exemplos vêm das fixtures reais em tests/fixtures/github/ (PR #7:
pull_detail.json, check_runs.json e reviews.json), como se ainda estivesse
aberto.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import ConfigDict, Field

from api.schemas.common import ApiModel


class PullBadge(StrEnum):
    """Estado de um PR aberto, numa palavra (a de maior prioridade vale).

    - `draft`: PR em rascunho; não pode ser aprovado nem mergeado.
    - `conflict`: conflito com a branch base (`mergeable_state` "dirty").
    - `checks_failed`: algum check falhou (ou foi cancelado, deu timeout...).
    - `waiting_checks`: algum check ainda está rodando ou na fila, ou o PR
      ainda não tem nenhum check contado.
    - `computing`: o GitHub ainda está calculando se dá para mergear
      (`mergeable_state` "unknown", ausente ou desconhecido).
    - `needs_approval`: checks verdes, mas a proteção da `main` bloqueia
      (`mergeable_state` "blocked"): falta aprovação.
    - `ready`: pronto para mergear (`mergeable_state` "clean", "unstable" ou
      "has_hooks").
    """

    DRAFT = "draft"
    CONFLICT = "conflict"
    CHECKS_FAILED = "checks_failed"
    WAITING_CHECKS = "waiting_checks"
    COMPUTING = "computing"
    NEEDS_APPROVAL = "needs_approval"
    READY = "ready"


_AUTHOR_EXAMPLE = {
    "login": "alv4roso4res",
    "avatarUrl": "https://avatars.githubusercontent.com/u/299255407?v=4",
}
_CHECKS_EXAMPLE = {"passed": 1, "failed": 0, "pending": 0}
_PULL_EXAMPLE = {
    "number": 7,
    "title": "feat(api): rotas de pipeline (cards 1 e 2)",
    "author": _AUTHOR_EXAMPLE,
    "createdAt": "2026-11-11T01:50:49Z",
    "htmlUrl": "https://github.com/alv4roso4res/adec/pull/7",
    "headSha": "3a97b4d0ca1ac84a3cb03e1bc47af5a53912a9bb",
    "checks": _CHECKS_EXAMPLE,
    "approvals": 1,
    "badge": "ready",
    "canApprove": False,
    "canMerge": True,
}


class PullAuthor(ApiModel):
    """Autor (quem abriu) o PR."""

    model_config = ConfigDict(json_schema_extra={"examples": [_AUTHOR_EXAMPLE]})

    login: str = Field(description="Login no GitHub.", examples=["alv4roso4res"])
    avatar_url: str = Field(
        description="URL do avatar no GitHub.",
        examples=[_AUTHOR_EXAMPLE["avatarUrl"]],
    )


class PullChecks(ApiModel):
    """Contagem dos checks do último commit do PR (execução mais recente de
    cada check). Checks `skipped`/`neutral` não entram em nenhuma contagem."""

    model_config = ConfigDict(json_schema_extra={"examples": [_CHECKS_EXAMPLE]})

    passed: int = Field(description="Checks concluídos com sucesso.", examples=[1])
    failed: int = Field(
        description="Checks concluídos sem sucesso (falha, cancelado, timeout...).",
        examples=[0],
    )
    pending: int = Field(
        description="Checks ainda na fila ou rodando.",
        examples=[0],
    )


class PullItem(ApiModel):
    """Um PR aberto, com checks, aprovações, badge e o que o painel pode fazer."""

    model_config = ConfigDict(json_schema_extra={"examples": [_PULL_EXAMPLE]})

    number: int = Field(description="Número do PR.", examples=[7])
    title: str = Field(description="Título do PR.", examples=[_PULL_EXAMPLE["title"]])
    author: PullAuthor = Field(
        description="Quem abriu o PR.",
        examples=[_AUTHOR_EXAMPLE],
    )
    created_at: datetime = Field(
        description="Quando o PR foi aberto (ISO 8601 UTC).",
        examples=["2026-11-11T01:50:49Z"],
    )
    html_url: str = Field(
        description="Link do PR no GitHub.",
        examples=[_PULL_EXAMPLE["htmlUrl"]],
    )
    head_sha: str = Field(
        description="SHA completo do último commit do PR.",
        examples=[_PULL_EXAMPLE["headSha"]],
    )
    checks: PullChecks = Field(
        description="Checks do último commit do PR.",
        examples=[_CHECKS_EXAMPLE],
    )
    approvals: int = Field(
        description=(
            "Revisores cujo review mais recente (ignorando comentários) é uma "
            "aprovação."
        ),
        examples=[1],
    )
    badge: PullBadge = Field(
        description="Estado do PR numa palavra (ver PullBadge).",
        examples=["needs_approval"],
    )
    can_approve: bool = Field(
        description=(
            "true se o painel pode aprovar: escrita ligada, dono do token "
            "conhecido, PR de outra pessoa, fora de rascunho e ainda não "
            "aprovado pelo dono do token."
        ),
        examples=[True],
    )
    can_merge: bool = Field(
        description=(
            "true se a escrita está ligada. Fica true mesmo com o PR bloqueado, "
            "de propósito: a demo mostra o GitHub recusando o merge."
        ),
        examples=[True],
    )
