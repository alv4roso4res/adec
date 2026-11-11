import pytest

from api.config import Settings
from api.errors import GitHubError

from .fakes import FakeGitHubClient

ACTIONS = ["approve", "merge"]


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        github_token="token-de-teste",
        github_owner="owner-teste",
        github_repo="repo-teste",
        enable_write_actions=True,
    )


@pytest.mark.parametrize("action", ACTIONS)
def test_write_disabled_returns_403_without_calling_github(
    client, use_fake, settings, action
):
    settings.enable_write_actions = False
    fake = use_fake(FakeGitHubClient())

    response = client.post(f"/api/pulls/7/{action}")

    assert response.status_code == 403
    assert response.json() == {"detail": "Ações de escrita estão desligadas"}
    assert fake.calls == []


def test_approve_returns_write_result(client, use_fake):
    fake = use_fake(FakeGitHubClient())

    response = client.post("/api/pulls/7/approve")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "message": "PR #7 aprovado"}
    assert fake.calls == [("approve_pull", {"number": 7})]


def test_merge_returns_write_result_with_short_sha(client, use_fake):
    fake = use_fake(FakeGitHubClient(merge_result={"sha": "3a97b4d0ca1ac84a3cb0"}))

    response = client.post("/api/pulls/7/merge")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "message": "PR #7 mergeado (3a97b4d)"}
    assert fake.calls == [("merge_pull", {"number": 7})]


def test_merge_refused_by_github_returns_409_with_original_detail(client, use_fake):
    message = "At least 1 approving review is required by reviewers with write access."
    use_fake(FakeGitHubClient(error=GitHubError(405, message)))

    response = client.post("/api/pulls/7/merge")

    assert response.status_code == 409
    assert response.json() == {"detail": message}


def test_merge_conflict_from_github_returns_409(client, use_fake):
    message = "Head branch was modified. Review and try the merge again."
    use_fake(FakeGitHubClient(error=GitHubError(409, message)))

    response = client.post("/api/pulls/7/merge")

    assert response.status_code == 409
    assert response.json() == {"detail": message}


def test_approve_own_pull_returns_422_with_original_detail(client, use_fake):
    message = "Unprocessable Entity: Can not approve your own pull request"
    use_fake(FakeGitHubClient(error=GitHubError(422, message)))

    response = client.post("/api/pulls/7/approve")

    assert response.status_code == 422
    assert response.json() == {"detail": message}


@pytest.mark.parametrize("action", ACTIONS)
@pytest.mark.parametrize("number", ["0", "-1", "abc"])
def test_invalid_number_returns_422_without_calling_github(
    client, use_fake, action, number
):
    fake = use_fake(FakeGitHubClient())

    response = client.post(f"/api/pulls/{number}/{action}")

    assert response.status_code == 422
    assert fake.calls == []


@pytest.mark.parametrize("action", ACTIONS)
def test_get_is_not_allowed_on_write_routes(client, action):
    assert client.get(f"/api/pulls/7/{action}").status_code == 405


@pytest.mark.parametrize(
    ("path", "operation_id"),
    [("/api/pulls/{number}/approve", "approve_pull"), ("/api/pulls/{number}/merge", "merge_pull")],
)
def test_write_routes_document_errors(app, path, operation_id):
    operation = app.openapi()["paths"][path]["post"]

    assert operation["operationId"] == operation_id
    assert {"403", "409", "422", "502", "503"} <= set(operation["responses"])
