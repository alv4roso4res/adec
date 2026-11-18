"""Monta o mapa de branches (card 7) a partir dos dados crus do GitHub.

Função pura: não faz requisição e nunca altera os dicts/listas recebidos (o
cache do GitHubClient devolve o mesmo objeto a cada chamada).

Como o mapa é montado:

1. **Linha da main:** a partir do commit mais novo, segue sempre o primeiro
   pai. Isso pula os commits que vieram das branches e deixa só a main.
2. **Branches mergeadas:** cada commit da main com dois pais é um merge. O
   segundo pai é a ponta da branch; seguindo o primeiro pai dela até cair na
   main, saem os commits da branch e o ponto de onde ela saiu (`forkSha`). O
   nome vem da mensagem do merge ("Merge pull request #20 from dono/branch").
3. **Branches abertas:** as que existem no GitHub, com os commits e o ponto de
   saída que o `compare` da main com elas devolve.
"""

import re
from collections.abc import Mapping, Sequence
from typing import Any

from api.schemas.branches import BranchLine, BranchMap, BranchState, MapCommit
from api.schemas.commits import CommitAuthor

Raw = Mapping[str, Any]

SHORT_SHA_LENGTH = 7

_MERGE_PULL = re.compile(r"^Merge pull request #(\d+) from [^/\s]+/(\S+)")
_MERGE_BRANCH = re.compile(r"^Merge branch '([^']+)'")


def build_branch_map(
    *,
    commits: Sequence[Raw],
    open_branches: Sequence[tuple[Raw, Raw]],
    pulls: Sequence[Raw],
    repo_url: str,
    default_branch: str = "main",
    limit: int,
) -> BranchMap:
    """`commits`: commits da main (mais novo primeiro, com `parents`).
    `open_branches`: pares (branch de GET /branches, resultado do compare).
    `pulls`: PRs abertos, para achar o PR de cada branch aberta.
    `limit`: quantos commits da linha da main entram no mapa."""
    by_sha = {c["sha"]: c for c in commits}
    chain = first_parent_chain(commits)
    on_main = {c["sha"] for c in chain}
    window = chain[:limit]

    merged = merged_branches(window, by_sha, on_main, repo_url)
    already_merged = {c.sha for line in merged for c in line.commits}
    # Branch mergeada que ninguém apagou já aparece pelo merge: não repete.
    opened = [
        open_branch(branch, comparison, pulls, repo_url)
        for branch, comparison in open_branches
        if branch["commit"]["sha"] not in already_merged
    ]

    return BranchMap(
        default_branch=default_branch,
        mainline=[to_map_commit(c) for c in reversed(window)],
        branches=sorted(merged + opened, key=_first_commit_date),
    )


def first_parent_chain(commits: Sequence[Raw]) -> list[Raw]:
    """Linha da main, do mais novo para o mais antigo, só pelo primeiro pai."""
    if not commits:
        return []
    by_sha = {c["sha"]: c for c in commits}
    chain: list[Raw] = []
    sha: str | None = commits[0]["sha"]
    while sha is not None and sha in by_sha:
        commit = by_sha[sha]
        chain.append(commit)
        sha = _parent(commit, 0)
    return chain


def merged_branches(
    window: Sequence[Raw],
    by_sha: Mapping[str, Raw],
    on_main: set[str],
    repo_url: str,
) -> list[BranchLine]:
    lines: list[BranchLine] = []
    # Do merge mais antigo para o mais novo: se uma branch foi mergeada duas
    # vezes, os commits antigos ficam com o primeiro merge.
    seen: set[str] = set()
    for merge in reversed(window):
        tip = _parent(merge, 1)
        if tip is None:
            continue

        own: list[Raw] = []
        sha: str | None = tip
        while sha is not None and sha in by_sha and sha not in on_main and sha not in seen:
            own.append(by_sha[sha])
            sha = _parent(by_sha[sha], 0)
        if not own:
            continue
        seen.update(c["sha"] for c in own)
        own.reverse()
        # Branch criada a partir de outra branch: segue pelos commits já
        # contados até achar a main, que vira o ponto de saída no mapa.
        while sha is not None and sha in by_sha and sha not in on_main:
            sha = _parent(by_sha[sha], 0)

        pr_number, name = parse_merge_message(_message(merge))
        commits = [to_map_commit(c) for c in own]
        lines.append(
            BranchLine(
                name=name or f"merge {merge['sha'][:SHORT_SHA_LENGTH]}",
                state=BranchState.MERGED,
                pr_number=pr_number,
                html_url=f"{repo_url}/pull/{pr_number}" if pr_number else merge["html_url"],
                fork_sha=sha if sha in on_main else None,
                merge_sha=merge["sha"],
                ahead_by=len(commits),
                behind_by=0,
                author=commits[-1].author,
                commits=commits,
            )
        )
    return lines


def open_branch(
    branch: Raw,
    comparison: Raw,
    pulls: Sequence[Raw],
    repo_url: str,
) -> BranchLine:
    name = branch["name"]
    pull = next((p for p in pulls if (p.get("head") or {}).get("ref") == name), None)
    commits = [to_map_commit(c) for c in comparison.get("commits") or []]
    base = comparison.get("merge_base_commit") or {}
    return BranchLine(
        name=name,
        state=BranchState.OPEN,
        pr_number=pull["number"] if pull else None,
        html_url=pull["html_url"] if pull else f"{repo_url}/tree/{name}",
        fork_sha=base.get("sha"),
        merge_sha=None,
        ahead_by=comparison.get("ahead_by", len(commits)),
        behind_by=comparison.get("behind_by", 0),
        author=commits[-1].author if commits else None,
        commits=commits,
    )


def parse_merge_message(message: str) -> tuple[int | None, str | None]:
    """(número do PR, nome da branch) a partir da mensagem de um merge."""
    if match := _MERGE_PULL.match(message):
        return int(match.group(1)), match.group(2)
    if match := _MERGE_BRANCH.match(message):
        return None, match.group(1)
    return None, None


def to_map_commit(raw: Raw) -> MapCommit:
    commit = raw["commit"]
    account = raw.get("author") or {}
    return MapCommit(
        sha=raw["sha"],
        short_sha=raw["sha"][:SHORT_SHA_LENGTH],
        message=_message(raw),
        author=CommitAuthor(
            login=account.get("login"),
            name=commit["author"]["name"],
            avatar_url=account.get("avatar_url"),
        ),
        committed_at=commit["committer"]["date"],
        html_url=raw["html_url"],
    )


def _parent(raw: Raw, index: int) -> str | None:
    parents = raw.get("parents") or []
    return parents[index]["sha"] if len(parents) > index else None


def _message(raw: Raw) -> str:
    message = raw["commit"].get("message") or ""
    return message.splitlines()[0] if message else ""


def _first_commit_date(line: BranchLine) -> tuple[bool, str]:
    # Branch aberta sem commits (acabou de sair da main) vai para o fim.
    if not line.commits:
        return True, ""
    return False, line.commits[0].committed_at.isoformat()
