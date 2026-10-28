import pytest
from fastapi.testclient import TestClient

from api.errors import GitHubError


@pytest.mark.parametrize(
    ("status", "rate_limited", "expected"),
    [
        (401, False, 502),
        (403, False, 502),  # 403 de auth/permissão
        (403, True, 503),  # 403 de rate limit
        (429, False, 503),
        (405, False, 409),  # merge não permitido
        (404, False, 404),
        (500, False, 502),
    ],
)
def test_github_error_status_mapping(status, rate_limited, expected):
    error = GitHubError(status, "x", rate_limited=rate_limited)

    assert error.http_status == expected


def test_handler_returns_detail_json(app):
    @app.get("/boom")
    def boom():
        raise GitHubError(405, "Pull request não é mergeável")

    with TestClient(app) as client:
        response = client.get("/boom")

    assert response.status_code == 409
    assert response.json() == {"detail": "Pull request não é mergeável"}
