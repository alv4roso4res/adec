import pytest

from api.errors import GitHubError
from api.routes.branches import COMMITS_WINDOW, MAX_OPEN_BRANCHES

from .fakes import RATE_LIMIT, FakeGitHubClient


def make_commit(sha: str, parents: list[str], message: str, minute: int) -> dict:
    return {
        "sha": sha,
        "html_url": f"https://github.com/owner-teste/repo-teste/commit/{sha}",
        "parents": [{"sha": p} for p in parents],
        "author": {"login": "ana", "avatar_url": "https://avatars/ana"},
        "commit": {
            "message": message,
            "author": {"name": "Ana"},
            "committer": {"date": f"2026-11-12T10:{minute:02d}:00Z"},
        },
    }


# Main: A -> M1 (merge #1 de B1) -> M2 (merge #2 de C1) -> P (push direto).
A = make_commit("a" * 40, [], "primeiro commit", 0)
B1 = make_commit("b1" * 20, ["a" * 40], "feat: b", 1)
M1 = make_commit("m1" * 20, ["a" * 40, "b1" * 20], "Merge pull request #1 from dono/feat/b", 2)
C1 = make_commit("c1" * 20, ["m1" * 20], "feat: c", 3)
M2 = make_commit("m2" * 20, ["m1" * 20, "c1" * 20], "Merge pull request #2 from dono/feat/c", 4)
P = make_commit("p" * 40, ["m2" * 20], "fix: push direto", 5)
HISTORY = [P, M2, C1, M1, B1, A]


def test_branches_returns_camel_case(client, use_fake, settings):
    fake = use_fake(FakeGitHubClient(commits=HISTORY, branches=[{"name": "main"}]))

    response = client.get("/api/branches")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"defaultBranch", "mainline", "branches"}
    assert body["defaultBranch"] == "main"
    assert len(body["mainline"]) == 4
    assert set(body["mainline"][0]) == {
        "sha",
        "shortSha",
        "message",
        "author",
        "committedAt",
        "htmlUrl",
    }
    branch = body["branches"][0]
    assert set(branch) == {
        "name",
        "state",
        "prNumber",
        "htmlUrl",
        "forkSha",
        "mergeSha",
        "aheadBy",
        "behindBy",
        "author",
        "commits",
    }
    assert branch["htmlUrl"] == "https://github.com/owner-teste/repo-teste/pull/1"
    assert ("list_commits", {"branch": "main", "limit": COMMITS_WINDOW}) in fake.calls
    # Mesma chamada de PRs do card 3 (sai do cache).
    assert ("list_pulls", {"state": "open", "limit": settings.pulls_limit}) in fake.calls
    # Só a main existe: nenhum compare.
    assert not [c for c in fake.calls if c[0] == "compare"]


def test_branches_compares_each_open_branch(client, use_fake):
    tip = make_commit("e1" * 20, ["p" * 40], "feat: mapa", 9)
    fake = use_fake(
        FakeGitHubClient(
            commits=HISTORY,
            branches=[
                {"name": "feat/mapa", "commit": {"sha": tip["sha"]}},
                {"name": "main", "commit": {"sha": P["sha"]}},
            ],
            comparisons={
                "feat/mapa": {
                    "ahead_by": 1,
                    "behind_by": 0,
                    "merge_base_commit": {"sha": P["sha"]},
                    "commits": [tip],
                }
            },
        )
    )

    response = client.get("/api/branches")

    assert response.status_code == 200
    opened = [b for b in response.json()["branches"] if b["state"] == "open"]
    assert [(b["name"], b["forkSha"], b["aheadBy"]) for b in opened] == [
        ("feat/mapa", P["sha"], 1)
    ]
    assert ("compare", {"base": "main", "head": "feat/mapa"}) in fake.calls


def test_branches_caps_open_branches(client, use_fake):
    names = [f"b{i:02d}" for i in range(MAX_OPEN_BRANCHES + 3)]
    fake = use_fake(
        FakeGitHubClient(
            commits=HISTORY,
            branches=[{"name": n, "commit": {"sha": P["sha"]}} for n in names],
        )
    )

    response = client.get("/api/branches")

    assert response.status_code == 200
    compared = [kw["head"] for name, kw in fake.calls if name == "compare"]
    assert compared == names[:MAX_OPEN_BRANCHES]


def test_branch_deleted_between_calls_is_skipped(client, use_fake):
    use_fake(
        FakeGitHubClient(
            commits=HISTORY,
            branches=[{"name": "sumiu", "commit": {"sha": M1["sha"]}}],
            comparisons={"sumiu": GitHubError(404, "Not Found")},
        )
    )

    response = client.get("/api/branches")

    assert response.status_code == 200
    assert all(b["state"] == "merged" for b in response.json()["branches"])


def test_compare_rate_limit_returns_503(client, use_fake):
    use_fake(
        FakeGitHubClient(
            commits=HISTORY,
            branches=[{"name": "feat/x", "commit": {"sha": P["sha"]}}],
            comparisons={"feat/x": RATE_LIMIT},
        )
    )

    response = client.get("/api/branches")

    assert response.status_code == 503
    assert response.json() == {"detail": "API rate limit exceeded"}


def test_branches_passes_limit(client, use_fake):
    use_fake(FakeGitHubClient(commits=HISTORY))

    response = client.get("/api/branches", params={"limit": 2})

    assert response.status_code == 200
    assert len(response.json()["mainline"]) == 2


@pytest.mark.parametrize("limit", [0, 51])
def test_branches_invalid_limit_returns_422(client, use_fake, limit):
    fake = use_fake(FakeGitHubClient())

    response = client.get("/api/branches", params={"limit": limit})

    assert response.status_code == 422
    assert fake.calls == []


def test_branches_rate_limit_returns_503(client, use_fake):
    use_fake(FakeGitHubClient(error=RATE_LIMIT))

    response = client.get("/api/branches")

    assert response.status_code == 503
