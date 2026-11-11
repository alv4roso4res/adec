import pytest

from api.config import Settings

from .fakes import RATE_LIMIT, FakeGitHubClient

SHA = "3a97b4d0ca1ac84a3cb03e1bc47af5a53912a9bb"


def make_settings(**changes) -> Settings:
    values = {
        "github_token": "token-de-teste",
        "github_owner": "owner-teste",
        "github_repo": "repo-teste",
        "enable_write_actions": True,
    }
    return Settings(_env_file=None, **(values | changes))


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def open_pull(github_fixture) -> dict:
    return github_fixture("pull_detail.json") | {"state": "open"}


@pytest.fixture
def fake_with_pr7(github_fixture, open_pull) -> FakeGitHubClient:
    return FakeGitHubClient(
        pulls=[open_pull],
        pull_details={7: open_pull | {"mergeable_state": "blocked"}},
        check_runs={SHA: github_fixture("check_runs.json")["check_runs"]},
        reviews={7: github_fixture("reviews.json")},
        user={"login": "GustaReis-bit"},
    )


def called(fake: FakeGitHubClient, name: str) -> list[dict]:
    return [kwargs for call, kwargs in fake.calls if call == name]


def test_pulls_returns_camel_case(client, use_fake, fake_with_pr7):
    use_fake(fake_with_pr7)

    response = client.get("/api/pulls")

    assert response.status_code == 200
    assert response.json() == [
        {
            "number": 7,
            "title": "feat(api): rotas de pipeline (cards 1 e 2)",
            "author": {
                "login": "alv4roso4res",
                "avatarUrl": "https://avatars.githubusercontent.com/u/299255407?v=4",
            },
            "createdAt": "2026-11-11T01:50:49Z",
            "htmlUrl": "https://github.com/alv4roso4res/adec/pull/7",
            "headSha": SHA,
            "checks": {"passed": 1, "failed": 0, "pending": 0},
            "approvals": 1,
            "badge": "needs_approval",
            # GustaReis-bit (dono do token no fake) já aprovou.
            "canApprove": False,
            "canMerge": True,
        }
    ]


def test_pulls_lists_open_pulls_with_pulls_limit(client, use_fake, settings):
    settings.pulls_limit = 3
    fake = use_fake(FakeGitHubClient())

    client.get("/api/pulls")

    assert called(fake, "list_pulls") == [{"state": "open", "limit": 3}]


def test_pulls_asks_token_login_when_writing_is_enabled(client, use_fake, fake_with_pr7):
    fake_with_pr7.user = {"login": "DrawnGZN"}
    fake = use_fake(fake_with_pr7)

    body = client.get("/api/pulls").json()

    assert called(fake, "get_authenticated_user") == [{}]
    assert body[0]["canApprove"] is True


@pytest.mark.parametrize(
    "settings",
    [
        make_settings(github_token=""),
        make_settings(enable_write_actions=False),
    ],
    ids=["sem-token", "escrita-desligada"],
)
def test_pulls_skips_authenticated_user(client, use_fake, fake_with_pr7, settings):
    fake = use_fake(fake_with_pr7)

    body = client.get("/api/pulls").json()

    assert called(fake, "get_authenticated_user") == []
    assert body[0]["canApprove"] is False
    assert body[0]["canMerge"] is settings.enable_write_actions


def test_pulls_fetches_details_checks_and_reviews_per_pull(
    client, use_fake, github_fixture
):
    # pulls.json: PRs reais #11, #10 e #9 (fechados; aqui tratados como abertos).
    pulls = github_fixture("pulls.json")
    fake = use_fake(FakeGitHubClient(pulls=pulls))

    response = client.get("/api/pulls")

    assert response.status_code == 200
    assert [p["number"] for p in response.json()] == [11, 10, 9]
    assert sorted(c["number"] for c in called(fake, "get_pull")) == [9, 10, 11]
    assert sorted(c["sha"] for c in called(fake, "list_check_runs")) == sorted(
        p["head"]["sha"] for p in pulls
    )
    assert sorted(c["number"] for c in called(fake, "list_reviews")) == [9, 10, 11]
    assert len(called(fake, "get_authenticated_user")) == 1


def test_pulls_rate_limit_returns_503(client, use_fake):
    use_fake(FakeGitHubClient(error=RATE_LIMIT))

    response = client.get("/api/pulls")

    assert response.status_code == 503
    assert response.json() == {"detail": "API rate limit exceeded"}


def test_pulls_without_open_pulls(client, use_fake):
    fake = use_fake(FakeGitHubClient())

    response = client.get("/api/pulls")

    assert response.status_code == 200
    assert response.json() == []
    # Sem PRs, nem detalhes nem /user.
    assert [call for call, _ in fake.calls] == ["list_pulls"]
