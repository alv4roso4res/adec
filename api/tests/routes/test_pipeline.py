from typing import Any

import pytest

from api.errors import GitHubError


class FakeGitHubClient:
    """Substitui o GitHubClient: devolve dados prontos e registra as chamadas."""

    def __init__(
        self,
        runs: list[dict[str, Any]] | None = None,
        jobs: list[dict[str, Any]] | None = None,
        error: GitHubError | None = None,
    ) -> None:
        self.runs = runs or []
        self.jobs = jobs or []
        self.error = error
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def list_workflow_runs(self, **kwargs: Any) -> list[dict[str, Any]]:
        self.calls.append(("list_workflow_runs", kwargs))
        if self.error:
            raise self.error
        return self.runs[: kwargs.get("limit") or None]

    async def list_run_jobs(self, run_id: int) -> list[dict[str, Any]]:
        self.calls.append(("list_run_jobs", {"run_id": run_id}))
        return self.jobs


@pytest.fixture
def runs(github_fixture) -> list[dict]:
    return github_fixture("workflow_runs.json")["workflow_runs"]


@pytest.fixture
def jobs(github_fixture) -> list[dict]:
    return github_fixture("run_jobs.json")["jobs"]


@pytest.fixture
def use_fake(app, client):
    # `client` já rodou o lifespan; troca o GitHubClient criado lá pelo fake.
    def install(fake: FakeGitHubClient) -> FakeGitHubClient:
        app.state.github_client = fake
        return fake

    return install


RATE_LIMIT = GitHubError(403, "API rate limit exceeded", rate_limited=True)


# ------------------------------------------------------------ /current


def test_current_returns_camel_case(client, use_fake, runs, jobs):
    fake = use_fake(FakeGitHubClient(runs=runs, jobs=jobs))

    response = client.get("/api/pipeline/current")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"run", "jobs"}
    assert set(body["run"]) == {
        "id",
        "status",
        "event",
        "branch",
        "headSha",
        "commitMessage",
        "actor",
        "startedAt",
        "durationSeconds",
        "htmlUrl",
    }
    assert body["run"]["status"] == "success"
    assert body["run"]["startedAt"] == "2026-11-11T00:57:48Z"
    assert set(body["jobs"][0]) == {"name", "status", "durationSeconds", "steps"}
    assert set(body["jobs"][0]["steps"][0]) == {"name", "status", "number"}

    assert fake.calls == [
        ("list_workflow_runs", {"branch": "main", "event": "push", "limit": 1}),
        ("list_run_jobs", {"run_id": runs[0]["id"]}),
    ]


def test_current_without_runs_returns_null(client, use_fake):
    fake = use_fake(FakeGitHubClient())

    response = client.get("/api/pipeline/current")

    assert response.status_code == 200
    assert response.json() == {"run": None, "jobs": []}
    # Sem run não há jobs para buscar.
    assert [name for name, _ in fake.calls] == ["list_workflow_runs"]


def test_current_rate_limit_returns_503(client, use_fake):
    use_fake(FakeGitHubClient(error=RATE_LIMIT))

    response = client.get("/api/pipeline/current")

    assert response.status_code == 503
    assert response.json() == {"detail": "API rate limit exceeded"}


# ------------------------------------------------------------ /history


def test_history_returns_camel_case(client, use_fake, runs, settings):
    fake = use_fake(FakeGitHubClient(runs=runs))

    response = client.get("/api/pipeline/history")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"runs", "stats"}
    assert set(body["runs"][0]) == {
        "id",
        "status",
        "event",
        "branch",
        "headSha",
        "durationSeconds",
        "createdAt",
    }
    assert set(body["stats"]) == {
        "total",
        "successRate",
        "avgDurationSeconds",
        "deploys",
        "byEvent",
    }
    assert body["stats"]["byEvent"] == {"push": 5, "pull_request": 5}
    # Sem ?limit=, usa HISTORY_LIMIT; todos os eventos e branches.
    assert fake.calls == [("list_workflow_runs", {"limit": settings.history_limit})]


def test_history_passes_limit(client, use_fake, runs):
    fake = use_fake(FakeGitHubClient(runs=runs))

    response = client.get("/api/pipeline/history", params={"limit": 3})

    assert response.status_code == 200
    assert response.json()["stats"]["total"] == 3
    assert fake.calls == [("list_workflow_runs", {"limit": 3})]


@pytest.mark.parametrize("limit", [0, 101])
def test_history_invalid_limit_returns_422(client, use_fake, limit):
    fake = use_fake(FakeGitHubClient())

    response = client.get("/api/pipeline/history", params={"limit": limit})

    assert response.status_code == 422
    assert fake.calls == []


def test_history_rate_limit_returns_503(client, use_fake):
    use_fake(FakeGitHubClient(error=RATE_LIMIT))

    response = client.get("/api/pipeline/history")

    assert response.status_code == 503
