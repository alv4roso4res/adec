import pytest
import respx
from httpx import Response

from api.config import Settings
from api.errors import GitHubError

from .fakes import RATE_LIMIT, FakeGitHubClient

GITHUB = "https://api.github.com"
REPO = "/repos/owner-teste/repo-teste"


@pytest.fixture
def settings() -> Settings:
    # Como a produção: rodando a imagem do commit e8eb3e0 (a main das fixtures).
    return Settings(
        _env_file=None,
        github_token="token-de-teste",
        github_owner="owner-teste",
        github_repo="repo-teste",
        app_version="e8eb3e0",
    )


def test_version_returns_camel_case(client, use_fake, commits, runs, packages):
    use_fake(FakeGitHubClient(commits=commits, runs=runs, packages=packages))

    response = client.get("/api/version")

    assert response.status_code == 200
    assert response.json() == {
        "running": "e8eb3e0",
        "mainSha": "e8eb3e0aa85bb8e7c0af9c52ae69197d024e941c",
        "images": [
            {"name": "adec-api", "publishedSha": "e8eb3e0"},
            {"name": "adec-frontend", "publishedSha": "e8eb3e0"},
        ],
        "state": "up_to_date",
    }


def test_version_reuses_card_2_and_card_6_calls(client, use_fake, settings):
    fake = use_fake(FakeGitHubClient())

    client.get("/api/pipeline/history")
    client.get("/api/commits")
    history_and_commits = list(fake.calls)
    fake.calls.clear()
    client.get("/api/version")

    version_calls = [(n, kw) for n, kw in fake.calls if n != "list_package_versions"]
    # Uma chamada de runs e uma de commits, com argumentos já usados pelos
    # cards 2 e 6 (repr: dicts não são hasheáveis; a ordem é paralela).
    assert len(version_calls) == 2
    assert {repr(c) for c in version_calls} <= {repr(c) for c in history_and_commits}
    assert [kw["image"] for n, kw in fake.calls if n == "list_package_versions"] == (
        settings.ghcr_images
    )


def test_version_package_not_published_yet(client, use_fake, commits, packages):
    use_fake(
        FakeGitHubClient(
            commits=commits,
            packages=packages,
            package_errors={"adec-frontend": GitHubError(404, "Package not found.")},
        )
    )

    response = client.get("/api/version")

    assert response.status_code == 200
    body = response.json()
    assert body["images"][1] == {"name": "adec-frontend", "publishedSha": None}
    assert body["state"] == "building"


def test_version_without_token_returns_502(client, use_fake, commits):
    use_fake(
        FakeGitHubClient(
            commits=commits,
            package_errors={"adec-api": GitHubError(401, "Requires authentication")},
        )
    )

    response = client.get("/api/version")

    assert response.status_code == 502
    assert response.json() == {"detail": "Requires authentication"}


def test_version_rate_limit_returns_503(client, use_fake):
    use_fake(FakeGitHubClient(error=RATE_LIMIT))

    response = client.get("/api/version")

    assert response.status_code == 503


def test_cards_2_6_then_5_hit_each_endpoint_once(client, github_fixture):
    # GitHubClient real + respx: o card 5 só busca o que é dele (os pacotes).
    with respx.mock(base_url=GITHUB, assert_all_called=True) as github:
        runs_route = github.get(f"{REPO}/actions/workflows/ci.yml/runs").mock(
            return_value=Response(200, json=github_fixture("workflow_runs.json"))
        )
        commits_route = github.get(f"{REPO}/commits").mock(
            return_value=Response(200, json=github_fixture("commits.json"))
        )
        package_routes = {
            img: github.get(f"/users/owner-teste/packages/container/{img}/versions").mock(
                return_value=Response(
                    200, json=github_fixture(f"package_versions_{img}.json")
                )
            )
            for img in ("adec-api", "adec-frontend")
        }

        assert client.get("/api/pipeline/history").status_code == 200
        assert client.get("/api/commits").status_code == 200
        version = client.get("/api/version")

    assert version.status_code == 200
    assert version.json()["state"] == "up_to_date"
    assert runs_route.call_count == 1
    assert commits_route.call_count == 1
    assert {img: r.call_count for img, r in package_routes.items()} == {
        "adec-api": 1,
        "adec-frontend": 1,
    }
