import asyncio
import json
from collections.abc import AsyncIterator

import httpx
import pytest
import respx

from api.config import Settings
from api.errors import GitHubError
from api.github.cache import ResponseCache
from api.github.client import TTL_PULLS, GitHubClient

BASE_URL = "https://api.github.com"
REPO = "/repos/owner-teste/repo-teste"


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def make_settings(**overrides) -> Settings:
    values = {
        "github_owner": "owner-teste",
        "github_repo": "repo-teste",
        "github_workflow_file": "ci.yml",
    }
    return Settings(_env_file=None, **(values | overrides))


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def mock() -> respx.MockRouter:
    # assert_all_called=False: cada teste registra só as rotas que usa.
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        yield router


@pytest.fixture
async def http() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        yield client


@pytest.fixture
def github(http, clock) -> GitHubClient:
    return GitHubClient(http, make_settings(), ResponseCache(clock=clock))


# ------------------------------------------------------------------ cache


async def test_second_call_within_ttl_uses_cache(github, mock, clock):
    route = mock.get(f"{REPO}/pulls").respond(200, json=[{"number": 1}])

    first = await github.list_pulls()
    clock.advance(TTL_PULLS - 1)
    second = await github.list_pulls()

    assert first == second == [{"number": 1}]
    assert route.call_count == 1


async def test_after_expiry_sends_if_none_match_and_304_reuses_data(
    github, mock, clock
):
    route = mock.get(f"{REPO}/pulls")
    route.side_effect = [
        httpx.Response(200, json=[{"number": 1}], headers={"ETag": '"v1"'}),
        httpx.Response(304),
    ]

    await github.list_pulls()
    clock.advance(TTL_PULLS)
    result = await github.list_pulls()

    assert result == [{"number": 1}]
    assert route.call_count == 2
    assert "If-None-Match" not in route.calls[0].request.headers
    assert route.calls[1].request.headers["If-None-Match"] == '"v1"'

    # O 304 renovou a validade: a próxima chamada não vai à rede.
    await github.list_pulls()
    assert route.call_count == 2


async def test_200_after_expiry_replaces_data_and_etag(github, mock, clock):
    route = mock.get(f"{REPO}/pulls")
    route.side_effect = [
        httpx.Response(200, json=[{"number": 1}], headers={"ETag": '"v1"'}),
        httpx.Response(200, json=[{"number": 2}], headers={"ETag": '"v2"'}),
        httpx.Response(304),
    ]

    await github.list_pulls()
    clock.advance(TTL_PULLS)
    assert await github.list_pulls() == [{"number": 2}]

    clock.advance(TTL_PULLS)
    assert await github.list_pulls() == [{"number": 2}]
    assert route.calls[2].request.headers["If-None-Match"] == '"v2"'


async def test_concurrent_identical_calls_make_one_request(github, mock):
    async def slow_response(request: httpx.Request) -> httpx.Response:
        # Cede o event loop, como uma requisição real: a segunda chamada
        # chega enquanto a primeira ainda espera a resposta.
        await asyncio.sleep(0)
        return httpx.Response(200, json=[{"number": 1}])

    route = mock.get(f"{REPO}/pulls").mock(side_effect=slow_response)

    results = await asyncio.gather(github.list_pulls(), github.list_pulls())

    assert results == [[{"number": 1}], [{"number": 1}]]
    assert route.call_count == 1


async def test_invalidate_pulls_only_affects_pulls(github, mock):
    pulls = mock.get(f"{REPO}/pulls").respond(200, json=[])
    commits = mock.get(f"{REPO}/commits").respond(200, json=[])

    await github.list_pulls()
    await github.list_commits()
    github.invalidate_pulls()
    await github.list_pulls()
    await github.list_commits()

    assert pulls.call_count == 2
    assert commits.call_count == 1


# ----------------------------------------------------------------- erros


async def test_403_rate_limited_maps_to_503(github, mock):
    mock.get(f"{REPO}/pulls").respond(
        403,
        json={"message": "API rate limit exceeded"},
        headers={"x-ratelimit-remaining": "0"},
    )

    with pytest.raises(GitHubError) as info:
        await github.list_pulls()

    assert info.value.rate_limited is True
    assert info.value.http_status == 503
    assert info.value.message == "API rate limit exceeded"


async def test_403_without_rate_limit_maps_to_502(github, mock):
    mock.get(f"{REPO}/pulls").respond(
        403,
        json={"message": "Resource not accessible"},
        headers={"x-ratelimit-remaining": "4999"},
    )

    with pytest.raises(GitHubError) as info:
        await github.list_pulls()

    assert info.value.rate_limited is False
    assert info.value.http_status == 502


async def test_404_keeps_status_and_github_message(github, mock):
    mock.get(f"{REPO}/pulls/99").respond(404, json={"message": "Not Found"})

    with pytest.raises(GitHubError) as info:
        await github.get_pull(99)

    assert info.value.http_status == 404
    assert info.value.message == "Not Found"


async def test_error_without_json_body_has_fallback_message(github, mock):
    mock.get(f"{REPO}/pulls").respond(500, text="<html>oops</html>")

    with pytest.raises(GitHubError) as info:
        await github.list_pulls()

    assert info.value.http_status == 502
    assert info.value.message == "Erro 500 do GitHub"


@pytest.mark.parametrize(
    "exc",
    [httpx.ReadTimeout("timeout"), httpx.ConnectError("sem rede")],
)
async def test_transport_errors_map_to_502(github, mock, exc):
    mock.get(f"{REPO}/pulls").mock(side_effect=exc)

    with pytest.raises(GitHubError) as info:
        await github.list_pulls()

    assert info.value.http_status == 502
    assert info.value.message == "Não foi possível falar com o GitHub"


async def test_errors_are_not_cached(github, mock):
    route = mock.get(f"{REPO}/pulls")
    route.side_effect = [
        httpx.Response(500, json={"message": "boom"}),
        httpx.Response(200, json=[{"number": 1}]),
    ]

    with pytest.raises(GitHubError):
        await github.list_pulls()

    assert await github.list_pulls() == [{"number": 1}]


# ------------------------------------------------------- endpoints/params


async def test_list_workflow_runs_uses_settings_file_and_query_params(http, mock):
    github = GitHubClient(
        http, make_settings(github_workflow_file="build.yml"), ResponseCache()
    )
    route = mock.get(f"{REPO}/actions/workflows/build.yml/runs").respond(
        200, json={"total_count": 1, "workflow_runs": [{"id": 7}]}
    )

    runs = await github.list_workflow_runs(branch="main", event="push", limit=3)

    assert runs == [{"id": 7}]
    params = route.calls.last.request.url.params
    assert params["branch"] == "main"
    assert params["event"] == "push"
    assert params["per_page"] == "3"


async def test_list_workflow_runs_defaults(github, mock):
    route = mock.get(f"{REPO}/actions/workflows/ci.yml/runs").respond(
        200, json={"workflow_runs": []}
    )

    await github.list_workflow_runs()

    params = route.calls.last.request.url.params
    assert dict(params) == {"per_page": "20"}  # history_limit; None não vai


async def test_list_package_versions_uses_ghcr_owner(http, mock):
    github = GitHubClient(
        http,
        make_settings(github_owner="Owner-Teste", ghcr_owner="Outro-Dono"),
        ResponseCache(),
    )
    route = mock.get("/users/outro-dono/packages/container/adec-api/versions").respond(
        200, json=[{"id": 1}]
    )

    assert await github.list_package_versions("adec-api") == [{"id": 1}]
    assert route.call_count == 1


@pytest.mark.parametrize(
    ("call", "path", "body", "expected"),
    [
        (
            lambda g: g.list_run_jobs(42),
            f"{REPO}/actions/runs/42/jobs",
            {"jobs": [{"id": 1}]},
            [{"id": 1}],
        ),
        (
            lambda g: g.list_check_runs("abc123"),
            f"{REPO}/commits/abc123/check-runs",
            {"check_runs": [{"id": 2}]},
            [{"id": 2}],
        ),
        (
            lambda g: g.list_reviews(5),
            f"{REPO}/pulls/5/reviews",
            [{"id": 3}],
            [{"id": 3}],
        ),
        (
            lambda g: g.list_contributors(),
            f"{REPO}/contributors",
            [{"login": "ana"}],
            [{"login": "ana"}],
        ),
        (lambda g: g.get_authenticated_user(), "/user", {"login": "eu"}, {"login": "eu"}),
    ],
)
async def test_endpoints_and_unwrapping(github, mock, call, path, body, expected):
    route = mock.get(path).respond(200, json=body)

    assert await call(github) == expected
    assert route.call_count == 1


async def test_list_pulls_and_commits_query_params(github, mock):
    pulls = mock.get(f"{REPO}/pulls").respond(200, json=[])
    commits = mock.get(f"{REPO}/commits").respond(200, json=[])

    await github.list_pulls()
    await github.list_commits(branch="dev", limit=8)

    assert dict(pulls.calls.last.request.url.params) == {
        "state": "open",
        "per_page": "5",
    }
    assert dict(commits.calls.last.request.url.params) == {
        "sha": "dev",
        "per_page": "8",
    }


# ---------------------------------------------------------------- escrita


async def test_approve_pull_sends_approve_event(github, mock):
    route = mock.post(f"{REPO}/pulls/7/reviews").respond(
        200, json={"id": 1, "state": "APPROVED"}
    )

    data = await github.approve_pull(7)

    assert data == {"id": 1, "state": "APPROVED"}
    assert route.call_count == 1
    assert json.loads(route.calls.last.request.content) == {"event": "APPROVE"}


@pytest.mark.parametrize("method", ["merge", "squash"])
async def test_merge_pull_sends_merge_method_from_settings(http, mock, method):
    github = GitHubClient(http, make_settings(merge_method=method), ResponseCache())
    route = mock.put(f"{REPO}/pulls/7/merge").respond(
        200, json={"sha": "abc1234def", "merged": True, "message": "Pull Request successfully merged"}
    )

    data = await github.merge_pull(7)

    assert data["sha"] == "abc1234def"
    assert json.loads(route.calls.last.request.content) == {"merge_method": method}


@pytest.mark.parametrize(
    ("call", "route_method", "path"),
    [
        ("approve_pull", "post", "/pulls/7/reviews"),
        ("merge_pull", "put", "/pulls/7/merge"),
    ],
)
async def test_write_success_invalidates_pulls_but_not_commits(
    github, mock, call, route_method, path
):
    pulls = mock.get(f"{REPO}/pulls").respond(200, json=[])
    commits = mock.get(f"{REPO}/commits").respond(200, json=[])
    getattr(mock, route_method)(f"{REPO}{path}").respond(200, json={"sha": "abc1234"})

    await github.list_pulls()
    await github.list_commits()
    await getattr(github, call)(7)
    await github.list_pulls()
    await github.list_commits()

    assert pulls.call_count == 2  # voltou à rede
    assert commits.call_count == 1  # continua em cache


async def test_write_failure_keeps_pulls_cache(github, mock):
    pulls = mock.get(f"{REPO}/pulls").respond(200, json=[])
    mock.put(f"{REPO}/pulls/7/merge").respond(405, json={"message": "não"})

    await github.list_pulls()
    with pytest.raises(GitHubError):
        await github.merge_pull(7)
    await github.list_pulls()

    assert pulls.call_count == 1


async def test_writes_are_never_cached(github, mock):
    route = mock.post(f"{REPO}/pulls/7/reviews").respond(200, json={"id": 1})

    await github.approve_pull(7)
    await github.approve_pull(7)

    assert route.call_count == 2


@pytest.mark.parametrize(
    ("call", "route_method", "path", "status", "message", "http_status"),
    [
        (
            "approve_pull",
            "post",
            "/pulls/7/reviews",
            422,
            "Unprocessable Entity: Can not approve your own pull request",
            422,
        ),
        (
            "merge_pull",
            "put",
            "/pulls/7/merge",
            405,
            "At least 1 approving review is required by reviewers with write access.",
            409,
        ),
        (
            "merge_pull",
            "put",
            "/pulls/7/merge",
            409,
            "Head branch was modified. Review and try the merge again.",
            409,
        ),
    ],
)
async def test_write_errors_keep_github_message(
    github, mock, call, route_method, path, status, message, http_status
):
    getattr(mock, route_method)(f"{REPO}{path}").respond(status, json={"message": message})

    with pytest.raises(GitHubError) as info:
        await getattr(github, call)(7)

    assert info.value.status_code == status
    assert info.value.http_status == http_status
    assert info.value.message == message


@pytest.mark.parametrize("call", ["approve_pull", "merge_pull"])
async def test_write_timeout_maps_to_502(github, mock, call):
    mock.post(f"{REPO}/pulls/7/reviews").mock(side_effect=httpx.ReadTimeout("timeout"))
    mock.put(f"{REPO}/pulls/7/merge").mock(side_effect=httpx.ReadTimeout("timeout"))

    with pytest.raises(GitHubError) as info:
        await getattr(github, call)(7)

    assert info.value.http_status == 502
    assert info.value.message == "Não foi possível falar com o GitHub"
