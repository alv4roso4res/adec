"""Resposta do card 6 (commits da main com o resultado do pipeline).

Os exemplos vêm da fixture real em tests/fixtures/github/commits.json.
"""

from datetime import datetime

from pydantic import ConfigDict, Field

from api.schemas.common import ApiModel, RunStatus

_SHA = "5ef37333051d1315423f73b75dec0ad76182796d"
_AVATAR = "https://avatars.githubusercontent.com/u/200959764?v=4"
_AUTHOR_EXAMPLE = {
    "login": "alv4roso4res",
    "name": "alv4roso4res",
    "avatarUrl": "https://avatars.githubusercontent.com/u/299255407?v=4",
}
_COMMIT_EXAMPLE = {
    "sha": _SHA,
    "shortSha": "5ef3733",
    "message": "Merge pull request #6 from alv4roso4res/feat/frontend-fundo-css",
    "author": _AUTHOR_EXAMPLE,
    "committedAt": "2026-11-11T00:57:44Z",
    "htmlUrl": f"https://github.com/alv4roso4res/adec/commit/{_SHA}",
    "pipelineStatus": "success",
}


class CommitAuthor(ApiModel):
    """Autor de um commit.

    `login` e `avatarUrl` ficam null quando o e-mail do commit não está ligado
    a nenhuma conta do GitHub; `name` sempre vem do próprio commit.
    """

    login: str | None = Field(
        description="Login no GitHub; null se o e-mail não está ligado a uma conta.",
        examples=["GustaReis-bit"],
    )
    name: str = Field(
        description="Nome gravado no commit (commit.author.name).",
        examples=["GustaReis"],
    )
    avatar_url: str | None = Field(
        description="URL do avatar no GitHub; null junto com login.",
        examples=[_AVATAR],
    )


class CommitItem(ApiModel):
    """Um commit da main com o resultado do pipeline que rodou nele."""

    model_config = ConfigDict(json_schema_extra={"examples": [_COMMIT_EXAMPLE]})

    sha: str = Field(description="SHA completo do commit.", examples=[_SHA])
    short_sha: str = Field(
        description="Primeiros 7 caracteres do SHA (como nas tags sha-xxxxxxx).",
        examples=["5ef3733"],
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
        examples=["2026-11-11T00:57:44Z"],
    )
    html_url: str = Field(
        description="Link do commit no GitHub.",
        examples=[_COMMIT_EXAMPLE["htmlUrl"]],
    )
    pipeline_status: RunStatus | None = Field(
        description=(
            "Status do run mais recente desse SHA, preferindo push a "
            "pull_request; null se o commit não aparece nos runs recentes."
        ),
        examples=["success"],
    )
