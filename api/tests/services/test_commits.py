import copy
from datetime import UTC, datetime

import pytest

from api.schemas.common import RunStatus
from api.services.commits import build_commits

# Na fixture de commits: 5ef3733 tem run de push na fixture de runs; 4ed40c4
# (veio do PR #6) só tem run de pull_request; e8eb3e0 é mais novo que todos os
# runs salvos.
SHA_PUSH = "5ef37333051d1315423f73b75dec0ad76182796d"
SHA_PR = "4ed40c4980571aaf3ce11326aa93b591e5a96747"


@pytest.fixture
def commits(github_fixture) -> list[dict]:
    return github_fixture("commits.json")


@pytest.fixture
def runs(github_fixture) -> list[dict]:
    return github_fixture("workflow_runs.json")["workflow_runs"]


def commit_by_sha(commits: list[dict], sha: str) -> dict:
    return next(c for c in commits if c["sha"] == sha)


def make_run(sha: str, event: str, conclusion: str, created_at: str) -> dict:
    return {
        "head_sha": sha,
        "event": event,
        "status": "completed",
        "conclusion": conclusion,
        "created_at": created_at,
    }


def test_build_commits_from_real_fixtures(commits, runs):
    items = build_commits(commits, runs)

    assert len(items) == len(commits) == 8
    first = items[0]
    assert first.sha == commits[0]["sha"]
    assert first.author.login == "GustaReis-bit"
    assert first.author.name == "GustaReis"
    assert first.author.avatar_url.startswith("https://avatars.githubusercontent.com/")
    assert first.committed_at == datetime(2026, 11, 11, 2, 3, 53, tzinfo=UTC)
    assert first.html_url.endswith(f"/commit/{commits[0]['sha']}")

    status = {item.short_sha: item.pipeline_status for item in items}
    assert status["5ef3733"] is RunStatus.SUCCESS
    assert status["4ed40c4"] is RunStatus.SUCCESS
    assert status["e8eb3e0"] is None


def test_message_keeps_only_first_line(commits):
    assert "\n" in commits[0]["commit"]["message"]

    item = build_commits(commits[:1], [])[0]

    assert item.message == "Merge pull request #8 from alv4roso4res/docs/api-openapi"


def test_short_sha_has_seven_chars(commits):
    item = build_commits(commits[:1], [])[0]

    assert item.short_sha == "e8eb3e0"
    assert len(item.short_sha) == 7
    assert item.sha.startswith(item.short_sha)


def test_author_without_github_account(commits):
    # E-mail do commit sem conta no GitHub: a API manda "author": null.
    commit = commits[0] | {"author": None}

    author = build_commits([commit], [])[0].author

    assert author.login is None
    assert author.avatar_url is None
    assert author.name == "GustaReis"


def test_push_wins_over_pull_request_on_same_sha(commits):
    commit = commit_by_sha(commits, SHA_PUSH)
    runs = [
        make_run(SHA_PUSH, "push", "failure", "2026-11-11T00:57:48Z"),
        # Mais recente, mas é de PR: não deve ganhar do push.
        make_run(SHA_PUSH, "pull_request", "success", "2026-11-11T01:30:00Z"),
    ]

    assert build_commits([commit], runs)[0].pipeline_status is RunStatus.FAILURE


def test_only_pull_request_run_is_used(commits, runs):
    commit = commit_by_sha(commits, SHA_PR)
    assert {r["event"] for r in runs if r["head_sha"] == SHA_PR} == {"pull_request"}

    assert build_commits([commit], runs)[0].pipeline_status is RunStatus.SUCCESS


@pytest.mark.parametrize("order", [1, -1], ids=["novo-primeiro", "antigo-primeiro"])
def test_latest_push_run_wins_regardless_of_order(commits, order):
    commit = commit_by_sha(commits, SHA_PUSH)
    runs = [
        make_run(SHA_PUSH, "push", "success", "2026-11-11T01:10:00Z"),  # re-run
        make_run(SHA_PUSH, "push", "failure", "2026-11-11T00:57:48Z"),
    ][::order]

    assert build_commits([commit], runs)[0].pipeline_status is RunStatus.SUCCESS


def test_commit_without_run_is_none(commits, runs):
    item = build_commits(commits[:1], runs)[0]

    assert item.pipeline_status is None


def test_in_progress_run_status_is_normalized(commits):
    commit = commit_by_sha(commits, SHA_PUSH)
    run = make_run(SHA_PUSH, "push", None, "2026-11-11T00:57:48Z") | {
        "status": "in_progress"
    }

    assert build_commits([commit], [run])[0].pipeline_status is RunStatus.IN_PROGRESS


def test_empty_commits():
    assert build_commits([], []) == []


def test_build_commits_does_not_mutate_input(commits, runs):
    # O cache do GitHubClient devolve o mesmo objeto a cada chamada.
    commits[0]["author"] = None
    commits_before = copy.deepcopy(commits)
    runs_before = copy.deepcopy(runs)

    build_commits(commits, runs)

    assert commits == commits_before
    assert runs == runs_before
