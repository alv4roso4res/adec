"""Resposta do card 7 (mapa de branches, estilo mapa de metrô).

A `main` é a linha principal; cada branch é uma linha que sai de um commit da
main (`forkSha`) e, se já foi mergeada, volta nela no commit de merge
(`mergeSha`). Os exemplos são do histórico real do repositório (PR #20).
"""

from datetime import datetime
from enum import StrEnum

from pydantic import ConfigDict, Field

from api.schemas.commits import CommitAuthor
from api.schemas.common import ApiModel

_MERGE_SHA = "91b463bd6534842b58d38e086a3ae0fa83452870"
_FORK_SHA = "adc0b98b521f5752cefb43c8b0680d0ca92274c3"
_BRANCH_SHA = "d901c86355460696324bbe0909fe6802eb8a53eb"
_AUTHOR_EXAMPLE = {
    "login": "GustaReis-bit",
    "name": "GustaReis",
    "avatarUrl": "https://avatars.githubusercontent.com/u/200959764?v=4",
}
_COMMIT_EXAMPLE = {
    "sha": _BRANCH_SHA,
    "shortSha": "d901c86",
    "message": "feat(frontend): legenda clicável nos runs e scroll nos commits",
    "author": _AUTHOR_EXAMPLE,
    "committedAt": "2026-11-12T15:28:05Z",
    "htmlUrl": f"https://github.com/alv4roso4res/adec/commit/{_BRANCH_SHA}",
}
_BRANCH_EXAMPLE = {
    "name": "frontendcrrbug",
    "state": "merged",
    "prNumber": 20,
    "htmlUrl": "https://github.com/alv4roso4res/adec/pull/20",
    "forkSha": _FORK_SHA,
    "mergeSha": _MERGE_SHA,
    "aheadBy": 1,
    "behindBy": 0,
    "author": _AUTHOR_EXAMPLE,
    "commits": [_COMMIT_EXAMPLE],
}


class BranchState(StrEnum):
    """Situação de uma branch no mapa.

    - `merged`: já voltou para a main (aparece pelo commit de merge);
    - `open`: existe no GitHub e ainda não voltou para a main.
    """

    MERGED = "merged"
    OPEN = "open"


class MapCommit(ApiModel):
    """Uma "estação" do mapa: um commit da main ou de uma branch."""

    model_config = ConfigDict(json_schema_extra={"examples": [_COMMIT_EXAMPLE]})

    sha: str = Field(description="SHA completo do commit.", examples=[_BRANCH_SHA])
    short_sha: str = Field(
        description="Primeiros 7 caracteres do SHA.",
        examples=["d901c86"],
    )
    message: str = Field(
        description="Primeira linha da mensagem do commit.",
        examples=[_COMMIT_EXAMPLE["message"]],
    )
    author: CommitAuthor = Field(
        description="Quem escreveu o commit.",
        examples=[_AUTHOR_EXAMPLE],
    )
    committed_at: datetime = Field(
        description="Data do commit pelo committer (ISO 8601 UTC).",
        examples=["2026-11-12T15:28:05Z"],
    )
    html_url: str = Field(
        description="Link do commit no GitHub.",
        examples=[_COMMIT_EXAMPLE["htmlUrl"]],
    )


class BranchLine(ApiModel):
    """Uma branch: a linha que sai da main e (se mergeada) volta para ela."""

    model_config = ConfigDict(json_schema_extra={"examples": [_BRANCH_EXAMPLE]})

    name: str = Field(
        description="Nome da branch (para mergeadas, lido da mensagem do merge).",
        examples=["frontendcrrbug"],
    )
    state: BranchState = Field(
        description="`merged` se já voltou para a main; `open` se ainda não.",
        examples=["merged"],
    )
    pr_number: int | None = Field(
        description="Número do PR da branch; null se não há PR (ou não foi achado).",
        examples=[20],
    )
    html_url: str = Field(
        description="Link do PR no GitHub ou, sem PR, da própria branch.",
        examples=[_BRANCH_EXAMPLE["htmlUrl"]],
    )
    fork_sha: str | None = Field(
        description=(
            "Commit da main de onde a branch saiu; null se esse ponto ficou "
            "antes dos commits buscados."
        ),
        examples=[_FORK_SHA],
    )
    merge_sha: str | None = Field(
        description="Commit de merge na main; null enquanto a branch está aberta.",
        examples=[_MERGE_SHA],
    )
    ahead_by: int = Field(
        description="Commits da branch que não estão na main (antes do merge).",
        examples=[1],
    )
    behind_by: int = Field(
        description="Commits da main que a branch ainda não tem (0 se mergeada).",
        examples=[0],
    )
    author: CommitAuthor | None = Field(
        description="Autor do último commit da branch; null se ela não tem commits.",
        examples=[_AUTHOR_EXAMPLE],
    )
    commits: list[MapCommit] = Field(
        description="Commits próprios da branch, do mais antigo para o mais novo.",
        examples=[[_COMMIT_EXAMPLE]],
    )


class BranchMap(ApiModel):
    """Mapa de branches: a main e as linhas que saem (e voltam) dela."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "defaultBranch": "main",
                    "mainline": [{**_COMMIT_EXAMPLE, "sha": _MERGE_SHA}],
                    "branches": [_BRANCH_EXAMPLE],
                }
            ]
        }
    )

    default_branch: str = Field(
        description="Branch principal (a linha do meio do mapa).",
        examples=["main"],
    )
    mainline: list[MapCommit] = Field(
        description=(
            "Commits da main pela linha de primeiro pai (sem os commits que "
            "vieram das branches), do mais antigo para o mais novo."
        ),
        examples=[[{**_COMMIT_EXAMPLE, "sha": _MERGE_SHA}]],
    )
    branches: list[BranchLine] = Field(
        description=(
            "Branches mergeadas cujo merge está em `mainline`, mais as branches "
            "abertas, ordenadas pelo primeiro commit."
        ),
        examples=[[_BRANCH_EXAMPLE]],
    )
