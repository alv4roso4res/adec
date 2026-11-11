import pytest

from api.config import Settings

from .fakes import RATE_LIMIT, FakeGitHubClient


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        github_token="token-de-teste",
        github_owner="owner-teste",
        github_repo="repo-teste",
        team_logins="alv4roso4res,GustaReis-bit,DrawnGZN",
    )


def test_team_returns_camel_case(client, use_fake, pulls, contributors):
    use_fake(FakeGitHubClient(pulls=pulls, contributors=contributors))

    response = client.get("/api/team")

    assert response.status_code == 200
    body = response.json()
    assert [m["login"] for m in body] == ["alv4roso4res", "GustaReis-bit", "DrawnGZN"]
    assert set(body[0]) == {
        "login",
        "avatarUrl",
        "prsOpen",
        "prsMerged",
        "commits",
        "meetsRequirement",
    }
    assert body[2] == {
        "login": "DrawnGZN",
        "avatarUrl": "https://github.com/DrawnGZN.png",
        "prsOpen": 0,
        "prsMerged": 0,
        "commits": 0,
        "meetsRequirement": False,
    }


def test_team_lists_pulls_of_all_states(client, use_fake):
    fake = use_fake(FakeGitHubClient())

    client.get("/api/team")

    assert sorted(fake.calls, key=str) == [
        ("list_contributors", {}),
        ("list_pulls", {"state": "all", "limit": 100}),
    ]


def test_team_rate_limit_returns_503(client, use_fake):
    use_fake(FakeGitHubClient(error=RATE_LIMIT))

    response = client.get("/api/team")

    assert response.status_code == 503
    assert response.json() == {"detail": "API rate limit exceeded"}


def test_team_without_team_logins_skips_github(client, use_fake, settings):
    settings.team_logins = []
    fake = use_fake(FakeGitHubClient())

    response = client.get("/api/team")

    assert response.status_code == 200
    assert response.json() == []
    assert fake.calls == []
