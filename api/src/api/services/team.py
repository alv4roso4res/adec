"""Monta o card 4: um item por integrante de TEAM_LOGINS.

Função pura: recebe os dicts crus do GitHub (PRs de todos os estados e
contribuidores); não faz requisição e nunca altera o que recebe (o cache do
GitHubClient devolve o mesmo objeto). Pessoas fora do time são ignoradas.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from api.schemas.team import TeamMember

Raw = Mapping[str, Any]


def build_team(
    team_logins: Sequence[str],
    pulls: Sequence[Raw],
    contributors: Sequence[Raw],
) -> list[TeamMember]:
    """Integrantes na ordem de `team_logins`, mesmo sem atividade."""
    contributors_by_login = {
        c["login"].lower(): c for c in contributors if c.get("login")
    }
    pulls_by_login: dict[str, list[Raw]] = {}
    for pull in pulls:
        login = (pull.get("user") or {}).get("login")
        if login:
            pulls_by_login.setdefault(login.lower(), []).append(pull)

    return [
        _to_member(
            login,
            pulls_by_login.get(login.lower(), []),
            contributors_by_login.get(login.lower()),
        )
        for login in team_logins
    ]


def _to_member(
    configured_login: str,
    pulls: list[Raw],
    contributor: Raw | None,
) -> TeamMember:
    pull_author = pulls[0]["user"] if pulls else {}
    # Login e avatar como o GitHub devolve; senão, o configurado e o fallback.
    login = (contributor or {}).get("login") or pull_author.get("login") or configured_login
    avatar_url = (
        (contributor or {}).get("avatar_url")
        or pull_author.get("avatar_url")
        or f"https://github.com/{configured_login}.png"
    )
    return TeamMember(
        login=login,
        avatar_url=avatar_url,
        prs_open=sum(p.get("state") == "open" for p in pulls),
        prs_merged=sum(bool(p.get("merged_at")) for p in pulls),
        commits=(contributor or {}).get("contributions", 0),
        meets_requirement=bool(pulls),
    )
