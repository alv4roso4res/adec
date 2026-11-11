"""Transforma commits crus do GitHub na resposta do card 6.

Função pura: não faz requisição e nunca altera os dicts/listas recebidos (o
cache do GitHubClient devolve o mesmo objeto a cada chamada). O status do
pipeline sai dos runs já buscados para o card 2, sem chamada extra.
"""

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from api.schemas.commits import CommitAuthor, CommitItem
from api.schemas.common import RunStatus
from api.services.pipeline import normalize_status

Raw = Mapping[str, Any]

SHORT_SHA_LENGTH = 7


def build_commits(commits: Sequence[Raw], runs: Sequence[Raw]) -> list[CommitItem]:
    runs_by_sha = _latest_run_by_sha(runs)
    return [_to_commit(commit, runs_by_sha.get(commit["sha"])) for commit in commits]


def _latest_run_by_sha(runs: Sequence[Raw]) -> dict[str, Raw]:
    """Run escolhido para cada SHA: push primeiro, depois o mais recente.

    Commits que vieram de PR só têm run de pull_request; os da main têm push.
    Não depende da ordem da lista (compara created_at).
    """
    chosen: dict[str, Raw] = {}
    for run in runs:
        current = chosen.get(run["head_sha"])
        if current is None or _rank(run) > _rank(current):
            chosen[run["head_sha"]] = run
    return chosen


def _rank(run: Raw) -> tuple[bool, datetime]:
    return run.get("event") == "push", datetime.fromisoformat(run["created_at"])


def _to_commit(raw: Raw, run: Raw | None) -> CommitItem:
    commit = raw["commit"]
    account = raw.get("author") or {}
    message = commit.get("message") or ""
    pipeline_status: RunStatus | None = (
        normalize_status(run.get("status"), run.get("conclusion")) if run else None
    )
    return CommitItem(
        sha=raw["sha"],
        short_sha=raw["sha"][:SHORT_SHA_LENGTH],
        message=message.splitlines()[0] if message else "",
        author=CommitAuthor(
            login=account.get("login"),
            name=commit["author"]["name"],
            avatar_url=account.get("avatar_url"),
        ),
        committed_at=commit["committer"]["date"],
        html_url=raw["html_url"],
        pipeline_status=pipeline_status,
    )
