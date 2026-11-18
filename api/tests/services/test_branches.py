import pytest

from api.schemas.branches import BranchState
from api.services.branches import build_branch_map, parse_merge_message

REPO_URL = "https://github.com/owner-teste/repo-teste"


def make_commit(sha: str, parents: list[str], message: str, minute: int) -> dict:
    """Commit no formato do GitHub, só com os campos que o service lê."""
    return {
        "sha": sha,
        "html_url": f"{REPO_URL}/commit/{sha}",
        "parents": [{"sha": p} for p in parents],
        "author": {"login": "ana", "avatar_url": "https://avatars/ana"},
        "commit": {
            "message": message,
            "author": {"name": "Ana"},
            "committer": {"date": f"2026-11-12T10:{minute:02d}:00Z"},
        },
    }


# Histórico usado nos testes (o mais antigo embaixo):
#
#   P   push direto na main
#   M3  merge #3 (feat/d), que saiu de M1 e cruzou com o #2
#   M2  merge #2 (feat/c): C1 -> C2, saiu de M1
#   M1  merge #1 (feat/b): B1, saiu de A
#   A   primeiro commit
A = make_commit("a" * 40, [], "primeiro commit", 0)
B1 = make_commit("b1" * 20, ["a" * 40], "feat: b", 1)
M1 = make_commit("m1" * 20, ["a" * 40, "b1" * 20], "Merge pull request #1 from dono/feat/b", 2)
C1 = make_commit("c1" * 20, ["m1" * 20], "feat: c parte 1", 3)
D1 = make_commit("d1" * 20, ["m1" * 20], "feat: d", 4)
C2 = make_commit("c2" * 20, ["c1" * 20], "feat: c parte 2\n\ncorpo", 5)
M2 = make_commit("m2" * 20, ["m1" * 20, "c2" * 20], "Merge pull request #2 from dono/feat/c", 6)
M3 = make_commit("m3" * 20, ["m2" * 20, "d1" * 20], "Merge pull request #3 from dono/feat/d", 7)
P = make_commit("p" * 40, ["m3" * 20], "fix: push direto", 8)

# Como o GitHub devolve GET /commits: do mais novo para o mais antigo.
HISTORY = [P, M3, M2, C2, D1, C1, M1, B1, A]


def build(commits=HISTORY, open_branches=(), pulls=(), limit=15):
    return build_branch_map(
        commits=commits,
        open_branches=list(open_branches),
        pulls=list(pulls),
        repo_url=REPO_URL,
        limit=limit,
    )


def shas(commits) -> list[str]:
    return [c.sha for c in commits]


def test_mainline_follows_first_parent_oldest_first():
    result = build()

    assert result.default_branch == "main"
    assert shas(result.mainline) == [c["sha"] for c in (A, M1, M2, M3, P)]


def test_each_merge_becomes_a_merged_branch():
    result = build()

    by_name = {b.name: b for b in result.branches}
    assert list(by_name) == ["feat/b", "feat/c", "feat/d"]  # pelo 1º commit

    c = by_name["feat/c"]
    assert c.state is BranchState.MERGED
    assert c.pr_number == 2
    assert c.html_url == f"{REPO_URL}/pull/2"
    assert c.fork_sha == M1["sha"]
    assert c.merge_sha == M2["sha"]
    assert shas(c.commits) == [C1["sha"], C2["sha"]]
    assert c.commits[1].message == "feat: c parte 2"
    assert (c.ahead_by, c.behind_by) == (2, 0)
    assert c.author is not None and c.author.login == "ana"

    # feat/d saiu de M1 antes do merge do #2: as linhas se cruzam.
    assert by_name["feat/d"].fork_sha == M1["sha"]
    assert by_name["feat/d"].merge_sha == M3["sha"]
    assert by_name["feat/b"].fork_sha == A["sha"]


def test_limit_keeps_only_merges_inside_the_window():
    result = build(limit=2)

    assert shas(result.mainline) == [M3["sha"], P["sha"]]
    assert [b.name for b in result.branches] == ["feat/d"]
    # O ponto de saída fica antes da janela, mas continua sendo da main.
    assert result.branches[0].fork_sha == M1["sha"]


def test_branch_older_than_fetched_commits_has_no_fork():
    # Sem B1 e A na lista: o pai de B1 não foi buscado.
    result = build(commits=[M1, B1])

    (line,) = result.branches
    assert shas(line.commits) == [B1["sha"]]
    assert line.fork_sha is None


def test_branch_created_from_another_branch_forks_where_that_one_did():
    # E1 saiu de C1 (commit do #2), não da main; foi mergeado depois do #3.
    e1 = make_commit("e1" * 20, ["c1" * 20], "feat: e", 9)
    m4 = make_commit("m4" * 20, ["p" * 40, "e1" * 20], "Merge pull request #4 from dono/feat/e", 10)

    result = build(commits=[m4, e1, *HISTORY])

    line = next(b for b in result.branches if b.name == "feat/e")
    assert shas(line.commits) == [e1["sha"]]  # C1 continua sendo do #2
    assert line.fork_sha == M1["sha"]


def test_merge_without_pull_request_uses_branch_name_and_commit_link():
    merge = make_commit("m9" * 20, ["a" * 40, "b1" * 20], "Merge branch 'hotfix'", 9)

    (line,) = build(commits=[merge, B1, A]).branches

    assert line.name == "hotfix"
    assert line.pr_number is None
    assert line.html_url == merge["html_url"]


def test_open_branch_uses_compare_and_matches_pull_request():
    tip = make_commit("e1" * 20, ["p" * 40], "feat: mapa", 9)
    branch = {"name": "feat/mapa", "commit": {"sha": tip["sha"]}}
    comparison = {
        "ahead_by": 1,
        "behind_by": 0,
        "merge_base_commit": {"sha": P["sha"]},
        "commits": [tip],
    }
    pull = {"number": 21, "html_url": f"{REPO_URL}/pull/21", "head": {"ref": "feat/mapa"}}

    result = build(open_branches=[(branch, comparison)], pulls=[pull])

    line = result.branches[-1]
    assert line.name == "feat/mapa"
    assert line.state is BranchState.OPEN
    assert line.pr_number == 21
    assert line.html_url == f"{REPO_URL}/pull/21"
    assert line.fork_sha == P["sha"]
    assert line.merge_sha is None
    assert shas(line.commits) == [tip["sha"]]
    assert (line.ahead_by, line.behind_by) == (1, 0)


def test_open_branch_without_pull_or_commits():
    branch = {"name": "nova", "commit": {"sha": P["sha"]}}
    comparison = {"ahead_by": 0, "behind_by": 0, "merge_base_commit": {"sha": P["sha"]}, "commits": []}

    line = build(open_branches=[(branch, comparison)]).branches[-1]

    assert line.name == "nova"
    assert line.pr_number is None
    assert line.html_url == f"{REPO_URL}/tree/nova"
    assert line.commits == []
    assert line.author is None


def test_merged_branch_that_was_not_deleted_is_not_repeated():
    branch = {"name": "feat/c", "commit": {"sha": C2["sha"]}}
    comparison = {"ahead_by": 0, "behind_by": 3, "commits": []}

    result = build(open_branches=[(branch, comparison)])

    assert [b.name for b in result.branches] == ["feat/b", "feat/c", "feat/d"]
    assert all(b.state is BranchState.MERGED for b in result.branches)


def test_empty_history():
    result = build(commits=[])

    assert result.mainline == []
    assert result.branches == []


def test_does_not_mutate_input():
    commits = [dict(c) for c in HISTORY]
    before = repr(commits)

    build(commits=commits)

    assert repr(commits) == before


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Merge pull request #20 from alv4roso4res/frontendcrrbug", (20, "frontendcrrbug")),
        ("Merge pull request #19 from dono/feat/frontend-svg-gh", (19, "feat/frontend-svg-gh")),
        ("Merge branch 'hotfix'", (None, "hotfix")),
        ("Merge branch 'main' into feat/x", (None, "main")),
        ("feat: commit comum", (None, None)),
    ],
)
def test_parse_merge_message(message, expected):
    assert parse_merge_message(message) == expected
