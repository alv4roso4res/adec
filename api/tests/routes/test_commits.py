import pytest
import respx
from httpx import Response

from .fakes import RATE_LIMIT, FakeGitHubClient

GITHUB = "https://api.github.com"
REPO = "/repos/owner-teste/repo-teste"  # do fixture `settings` do conftest


def test_commits_returns_camel_case(client, use_fake, commits, runs):
    fake = use_fake(FakeGitHubClient(commits=commits, runs=runs))

    response = client.get("/api/commits")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 8
    assert set(body[0]) == {
        "sha",
        "shortSha",
        "message",
        "author",
        "committedAt",
        "htmlUrl",
        "pipelineStatus",
    }
    assert set(body[0]["author"]) == {"login", "name", "avatarUrl"}
    assert body[0]["committedAt"] == "2026-11-11T02:03:53Z"
    by_sha = {c["shortSha"]: c["pipelineStatus"] for c in body}
    assert by_sha["5ef3733"] == "success"
    assert by_sha["e8eb3e0"] is None
    assert ("list_commits", {"branch": "main", "limit": 8}) in fake.calls


def test_commits_passes_limit(client, use_fake, commits):
    fake = use_fake(FakeGitHubClient(commits=commits))

    response = client.get("/api/commits", params={"limit": 3})

    assert response.status_code == 200
    assert len(response.json()) == 3
    assert ("list_commits", {"branch": "main", "limit": 3}) in fake.calls


@pytest.mark.parametrize("limit", [0, 31])
def test_commits_invalid_limit_returns_422(client, use_fake, limit):
    fake = use_fake(FakeGitHubClient())

    response = client.get("/api/commits", params={"limit": limit})

    assert response.status_code == 422
    assert fake.calls == []


def test_commits_rate_limit_returns_503(client, use_fake):
    use_fake(FakeGitHubClient(error=RATE_LIMIT))

    response = client.get("/api/commits")

    assert response.status_code == 503
    assert response.json() == {"detail": "API rate limit exceeded"}


def test_commits_uses_same_runs_call_as_history(client, use_fake):
    fake = use_fake(FakeGitHubClient())

    client.get("/api/pipeline/history")
    client.get("/api/commits")

    runs_calls = [kwargs for name, kwargs in fake.calls if name == "list_workflow_runs"]
    assert len(runs_calls) == 2
    assert runs_calls[0] == runs_calls[1]


def test_history_then_commits_hits_runs_endpoint_once(client, github_fixture):
    # GitHubClient real (criado no lifespan) + respx: prova que o card 6 reaproveita
    # do cache os runs que o card 2 acabou de buscar.
    with respx.mock(base_url=GITHUB, assert_all_called=True) as github:
        runs_route = github.get(f"{REPO}/actions/workflows/ci.yml/runs").mock(
            return_value=Response(
                200,
                json=github_fixture("workflow_runs.json"),
                headers={"ETag": '"runs-v1"'},
            )
        )
        commits_route = github.get(f"{REPO}/commits").mock(
            return_value=Response(200, json=github_fixture("commits.json"))
        )

        history = client.get("/api/pipeline/history")
        commits = client.get("/api/commits")

    assert history.status_code == 200
    assert commits.status_code == 200
    assert runs_route.call_count == 1
    assert commits_route.call_count == 1
    assert commits.json()[4]["pipelineStatus"] == "success"  # 5ef3733
