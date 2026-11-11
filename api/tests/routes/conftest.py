import pytest

from .fakes import FakeGitHubClient


@pytest.fixture
def runs(github_fixture) -> list[dict]:
    return github_fixture("workflow_runs.json")["workflow_runs"]


@pytest.fixture
def jobs(github_fixture) -> list[dict]:
    return github_fixture("run_jobs.json")["jobs"]


@pytest.fixture
def commits(github_fixture) -> list[dict]:
    return github_fixture("commits.json")


@pytest.fixture
def packages(github_fixture) -> dict[str, list[dict]]:
    return {
        image: github_fixture(f"package_versions_{image}.json")
        for image in ("adec-api", "adec-frontend")
    }


@pytest.fixture
def use_fake(app, client):
    # `client` já rodou o lifespan; troca o GitHubClient criado lá pelo fake.
    def install(fake: FakeGitHubClient) -> FakeGitHubClient:
        app.state.github_client = fake
        return fake

    return install
