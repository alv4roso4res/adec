import copy
from datetime import UTC, datetime

import pytest

from api.schemas.common import RunStatus
from api.services.pipeline import (
    build_current,
    build_history,
    duration_seconds,
    normalize_status,
)

# Run real da fixture: push na main, 00:57:48 → 00:59:46 (118 s).
RUN_ID = 42935390858
NOW = datetime(2026, 11, 11, 1, 0, 0, tzinfo=UTC)


@pytest.fixture
def runs(github_fixture) -> list[dict]:
    return github_fixture("workflow_runs.json")["workflow_runs"]


@pytest.fixture
def jobs(github_fixture) -> list[dict]:
    return github_fixture("run_jobs.json")["jobs"]


def with_status(run: dict, status: str, conclusion: str | None = None) -> dict:
    return run | {"status": status, "conclusion": conclusion}


# ------------------------------------------------------------ normalização


@pytest.mark.parametrize(
    ("status", "conclusion", "expected"),
    [
        ("queued", None, RunStatus.QUEUED),
        ("waiting", None, RunStatus.QUEUED),
        ("requested", None, RunStatus.QUEUED),
        ("pending", None, RunStatus.QUEUED),
        ("in_progress", None, RunStatus.IN_PROGRESS),
        ("completed", "success", RunStatus.SUCCESS),
        ("completed", "cancelled", RunStatus.CANCELLED),
        ("completed", "skipped", RunStatus.SKIPPED),
        ("completed", "neutral", RunStatus.SKIPPED),
        ("completed", "failure", RunStatus.FAILURE),
        ("completed", "timed_out", RunStatus.FAILURE),
        ("completed", "action_required", RunStatus.FAILURE),
        ("completed", "startup_failure", RunStatus.FAILURE),
        ("completed", "stale", RunStatus.FAILURE),
        ("completed", "algo_novo", RunStatus.FAILURE),
        ("completed", None, RunStatus.FAILURE),
    ],
)
def test_normalize_status(status, conclusion, expected):
    assert normalize_status(status, conclusion) is expected


# ----------------------------------------------------------------- duração


def test_duration_completed_uses_end_date():
    assert (
        duration_seconds(
            RunStatus.SUCCESS, "2026-11-11T00:57:48Z", "2026-11-11T00:59:46Z", NOW
        )
        == 118
    )


def test_duration_in_progress_goes_until_now():
    assert (
        duration_seconds(
            RunStatus.IN_PROGRESS, "2026-11-11T00:58:30Z", "2026-11-11T00:58:31Z", NOW
        )
        == 90
    )


def test_duration_queued_is_none():
    assert duration_seconds(RunStatus.QUEUED, "2026-11-11T00:58:30Z", None, NOW) is None


def test_duration_without_start_is_none():
    assert duration_seconds(RunStatus.SUCCESS, None, "2026-11-11T00:59:46Z", NOW) is None


def test_duration_is_never_negative():
    # Relógio do GitHub um pouco à frente do nosso.
    assert duration_seconds(RunStatus.IN_PROGRESS, "2026-11-11T01:00:05Z", None, NOW) == 0


# ------------------------------------------------------------- card 1


def test_build_current_from_real_fixture(runs, jobs):
    current = build_current(runs[:1], jobs, NOW)

    run = current.run
    assert run is not None
    assert run.id == RUN_ID
    assert run.status is RunStatus.SUCCESS
    assert run.event == "push"
    assert run.branch == "main"
    assert run.head_sha == "5ef37333051d1315423f73b75dec0ad76182796d"
    assert run.actor == "alv4roso4res"
    assert run.started_at == datetime(2026, 11, 11, 0, 57, 48, tzinfo=UTC)
    assert run.duration_seconds == 118
    assert run.html_url.endswith(f"/actions/runs/{RUN_ID}")

    assert [(j.name, j.status, j.duration_seconds) for j in current.jobs] == [
        ("build-test", RunStatus.SUCCESS, 81),
        ("deploy", RunStatus.SUCCESS, 32),
    ]
    steps = current.jobs[0].steps
    assert steps[0].name == "Set up job"
    assert steps[0].number == 1
    assert all(s.status is RunStatus.SUCCESS for s in steps)


def test_commit_message_keeps_only_first_line(runs):
    # A mensagem do merge na fixture tem corpo depois de uma linha em branco.
    assert "\n" in runs[0]["head_commit"]["message"]

    run = build_current(runs[:1], [], NOW).run

    assert run.commit_message == (
        "Merge pull request #6 from alv4roso4res/feat/frontend-fundo-css"
    )


def test_build_current_without_runs():
    current = build_current([], [], NOW)

    assert current.run is None
    assert current.jobs == []


def test_build_current_in_progress_run(runs):
    run = runs[0] | {
        "status": "in_progress",
        "conclusion": None,
        "run_started_at": "2026-11-11T00:59:00Z",
    }

    current = build_current([run], [], NOW)

    assert current.run.status is RunStatus.IN_PROGRESS
    assert current.run.duration_seconds == 60


def test_build_current_queued_run(runs):
    run = with_status(runs[0], "queued")

    current = build_current([run], [], NOW)

    assert current.run.status is RunStatus.QUEUED
    assert current.run.duration_seconds is None


def test_failed_build_shows_deploy_skipped(runs, jobs):
    run = with_status(runs[0], "completed", "failure")
    build, deploy = jobs
    build = with_status(build, "completed", "failure")
    deploy = with_status(deploy, "completed", "skipped") | {
        "started_at": "2026-11-11T00:59:11Z",
        "completed_at": "2026-11-11T00:59:11Z",
        "steps": [],
    }

    current = build_current([run], [build, deploy], NOW)

    assert current.run.status is RunStatus.FAILURE
    assert [(j.name, j.status) for j in current.jobs] == [
        ("build-test", RunStatus.FAILURE),
        ("deploy", RunStatus.SKIPPED),
    ]
    assert current.jobs[1].duration_seconds == 0
    assert current.jobs[1].steps == []


# ------------------------------------------------------------- card 2


def test_build_history_from_real_fixture(runs):
    history = build_history(runs, NOW)

    assert len(history.runs) == 10
    first = history.runs[0]
    assert first.id == RUN_ID
    assert first.duration_seconds == 118
    assert first.created_at == datetime(2026, 11, 11, 0, 57, 48, tzinfo=UTC)

    stats = history.stats
    assert stats.total == 10
    assert stats.success_rate == 1.0
    assert stats.deploys == 5
    assert stats.by_event == {"push": 5, "pull_request": 5}


def test_stats_ignore_cancelled_skipped_and_unfinished_in_success_rate(runs):
    sample = [
        with_status(runs[0], "completed", "success"),
        with_status(runs[1], "completed", "failure"),
        with_status(runs[2], "completed", "success"),
        with_status(runs[3], "completed", "cancelled"),
        with_status(runs[4], "completed", "skipped"),
        with_status(runs[5], "in_progress"),
        with_status(runs[6], "queued"),
    ]

    stats = build_history(sample, NOW).stats

    assert stats.total == 7
    assert stats.success_rate == 0.667  # 2 / (2 + 1), arredondado em 3 casas


def test_stats_success_rate_none_without_success_or_failure(runs):
    sample = [
        with_status(runs[0], "completed", "cancelled"),
        with_status(runs[1], "in_progress"),
    ]

    assert build_history(sample, NOW).stats.success_rate is None


def test_stats_average_only_counts_finished_runs(runs):
    def run(index: int, status: str, conclusion: str | None, start: str, end: str):
        return with_status(runs[index], status, conclusion) | {
            "run_started_at": start,
            "updated_at": end,
        }

    sample = [
        run(0, "completed", "success", "2026-11-11T00:00:00Z", "2026-11-11T00:01:40Z"),
        run(1, "completed", "cancelled", "2026-11-11T00:00:00Z", "2026-11-11T00:00:51Z"),
        # Em andamento há 1 h: não pode puxar a média.
        run(2, "in_progress", None, "2026-11-11T00:00:00Z", "2026-11-11T00:00:01Z"),
        run(3, "queued", None, "2026-11-11T00:00:00Z", "2026-11-11T00:00:01Z"),
    ]

    history = build_history(sample, NOW)

    assert history.runs[2].duration_seconds == 3600
    assert history.stats.avg_duration_seconds == 76  # (100 + 51) / 2 = 75.5


def test_stats_deploys_and_by_event(runs):
    push_main = runs[0]  # push, main, success
    sample = [
        push_main,
        with_status(push_main, "completed", "failure"),
        push_main | {"head_branch": "outra"},
        push_main | {"event": "workflow_dispatch"},
        runs[1],  # pull_request, success
    ]

    stats = build_history(sample, NOW).stats

    assert stats.deploys == 1
    assert stats.by_event == {"push": 3, "workflow_dispatch": 1, "pull_request": 1}


def test_build_history_empty_list():
    history = build_history([], NOW)

    assert history.runs == []
    assert history.stats.total == 0
    assert history.stats.success_rate is None
    assert history.stats.avg_duration_seconds is None
    assert history.stats.deploys == 0
    assert history.stats.by_event == {}


# ------------------------------------------------------------ imutabilidade


def test_services_do_not_mutate_input(runs, jobs):
    # O cache do GitHubClient devolve o mesmo objeto a cada chamada.
    runs_before = copy.deepcopy(runs)
    jobs_before = copy.deepcopy(jobs)

    build_current(runs, jobs, NOW)
    build_history(runs, NOW)

    assert runs == runs_before
    assert jobs == jobs_before
