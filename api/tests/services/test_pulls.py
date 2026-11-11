import copy

import pytest

from api.schemas.pulls import PullBadge
from api.services.pulls import build_pulls

# Fixtures reais do PR #7 (já mergeado; os testes o tratam como aberto): checks
# build-test success + deploy skipped; 1 review APPROVED de GustaReis-bit;
# mergeable_state "unknown" (o GitHub não recalcula PR fechado).
NUMBER = 7
AUTHOR = "alv4roso4res"
TOKEN_LOGIN = "dono-do-token"


@pytest.fixture
def detail(github_fixture) -> dict:
    return github_fixture("pull_detail.json") | {"state": "open"}


@pytest.fixture
def pull(detail) -> dict:
    # O item de GET /pulls tem os mesmos campos usados que o detalhe.
    return copy.deepcopy(detail)


@pytest.fixture
def checks(github_fixture) -> list[dict]:
    return github_fixture("check_runs.json")["check_runs"]


@pytest.fixture
def reviews(github_fixture) -> list[dict]:
    return github_fixture("reviews.json")


def check(conclusion: str | None, status: str = "completed", name: str = "x") -> dict:
    return {"name": name, "status": status, "conclusion": conclusion}


def review(login: str, state: str) -> dict:
    return {"user": {"login": login}, "state": state}


GREEN = [check("success", name="build-test"), check("skipped", name="deploy")]


def build_one(
    pull,
    detail,
    checks=(),
    reviews=(),
    token_login=TOKEN_LOGIN,
    write_enabled=True,
    **detail_changes,
):
    return build_pulls(
        [pull],
        {NUMBER: detail | detail_changes},
        {NUMBER: list(checks)},
        {NUMBER: list(reviews)},
        token_login=token_login,
        write_enabled=write_enabled,
    )[0]


# ------------------------------------------------------------ fixtures reais


def test_build_pulls_from_real_fixtures(pull, detail, checks, reviews):
    item = build_one(pull, detail, checks, reviews)

    assert item.number == NUMBER
    assert item.title == "feat(api): rotas de pipeline (cards 1 e 2)"
    assert item.author.login == AUTHOR
    assert item.head_sha == "3a97b4d0ca1ac84a3cb03e1bc47af5a53912a9bb"
    # deploy (skipped) não conta.
    assert (item.checks.passed, item.checks.failed, item.checks.pending) == (1, 0, 0)
    assert item.approvals == 1
    assert item.badge is PullBadge.COMPUTING
    assert item.can_approve is True
    assert item.can_merge is True


def test_keeps_github_order_and_indexes_by_number(detail, checks):
    pulls = [detail | {"number": n} for n in (12, 8)]
    items = build_pulls(
        pulls,
        {12: detail | {"draft": True}, 8: detail | {"mergeable_state": "clean"}},
        {12: [], 8: checks},
        {},
        token_login=None,
        write_enabled=False,
    )

    assert [(i.number, i.badge) for i in items] == [
        (12, PullBadge.DRAFT),
        (8, PullBadge.READY),
    ]


# -------------------------------------------------------------------- badges


def test_badge_draft(pull, detail):
    assert build_one(pull, detail, GREEN, draft=True).badge is PullBadge.DRAFT


def test_badge_conflict(pull, detail):
    item = build_one(pull, detail, GREEN, mergeable_state="dirty")

    assert item.badge is PullBadge.CONFLICT


def test_badge_checks_failed(pull, detail):
    checks = [check("success"), check("failure")]
    item = build_one(pull, detail, checks, mergeable_state="blocked")

    assert item.badge is PullBadge.CHECKS_FAILED


def test_badge_waiting_checks_with_pending_check(pull, detail):
    checks = [check("success"), check(None, status="in_progress")]
    item = build_one(pull, detail, checks, mergeable_state="blocked")

    assert item.badge is PullBadge.WAITING_CHECKS


def test_badge_waiting_checks_without_any_check(pull, detail):
    item = build_one(pull, detail, [], mergeable_state="clean")

    assert item.checks.model_dump() == {"passed": 0, "failed": 0, "pending": 0}
    assert item.badge is PullBadge.WAITING_CHECKS


def test_badge_waiting_checks_when_only_skipped(pull, detail):
    item = build_one(pull, detail, [check("skipped")], mergeable_state="clean")

    assert item.badge is PullBadge.WAITING_CHECKS


@pytest.mark.parametrize("state", ["unknown", None, "behind", "estado-novo"])
def test_badge_computing(pull, detail, state):
    item = build_one(pull, detail, GREEN, mergeable_state=state)

    assert item.badge is PullBadge.COMPUTING


def test_badge_computing_without_mergeable_state(pull, detail):
    del detail["mergeable_state"]

    assert build_one(pull, detail, GREEN).badge is PullBadge.COMPUTING


def test_badge_needs_approval(pull, detail):
    item = build_one(pull, detail, GREEN, mergeable_state="blocked")

    assert item.badge is PullBadge.NEEDS_APPROVAL


@pytest.mark.parametrize("state", ["clean", "unstable", "has_hooks"])
def test_badge_ready(pull, detail, state):
    assert build_one(pull, detail, GREEN, mergeable_state=state).badge is PullBadge.READY


@pytest.mark.parametrize(
    ("changes", "checks", "expected"),
    [
        # draft vence conflito e checks falhando.
        ({"draft": True, "mergeable_state": "dirty"}, [check("failure")], PullBadge.DRAFT),
        # conflito vence checks falhando.
        ({"mergeable_state": "dirty"}, [check("failure")], PullBadge.CONFLICT),
        # checks falhando vencem checks pendentes.
        (
            {"mergeable_state": "blocked"},
            [check("failure"), check(None, status="queued")],
            PullBadge.CHECKS_FAILED,
        ),
        # checks pendentes vencem "calculando".
        ({"mergeable_state": "unknown"}, [check(None, "queued")], PullBadge.WAITING_CHECKS),
        # checks pendentes vencem "pronto".
        ({"mergeable_state": "clean"}, [check(None, "in_progress")], PullBadge.WAITING_CHECKS),
    ],
)
def test_badge_priority(pull, detail, changes, checks, expected):
    assert build_one(pull, detail, checks, **changes).badge is expected


# -------------------------------------------------------------------- checks


def test_check_counts(pull, detail):
    checks = [
        check("success"),
        check("success"),
        check("failure"),
        check("cancelled"),
        check("timed_out"),
        check("action_required"),
        check(None, status="queued"),
        check(None, status="in_progress"),
        check("skipped"),
        check("neutral"),
    ]

    counts = build_one(pull, detail, checks).checks

    assert (counts.passed, counts.failed, counts.pending) == (2, 4, 2)


def test_unknown_status_counts_as_pending(pull, detail):
    counts = build_one(pull, detail, [check(None, status="waiting")]).checks

    assert counts.pending == 1


# ------------------------------------------------------------------- reviews


def test_approved_then_changes_requested_does_not_count(pull, detail):
    reviews = [review("GustaReis-bit", "APPROVED"), review("GustaReis-bit", "CHANGES_REQUESTED")]

    assert build_one(pull, detail, GREEN, reviews).approvals == 0


def test_commented_after_approved_stays_approved(pull, detail):
    reviews = [review("GustaReis-bit", "APPROVED"), review("GustaReis-bit", "COMMENTED")]

    assert build_one(pull, detail, GREEN, reviews).approvals == 1


def test_changes_requested_then_approved_counts(pull, detail):
    reviews = [review("DrawnGZN", "CHANGES_REQUESTED"), review("DrawnGZN", "APPROVED")]

    assert build_one(pull, detail, GREEN, reviews).approvals == 1


def test_dismissed_approval_does_not_count(pull, detail):
    reviews = [review("GustaReis-bit", "APPROVED"), review("GustaReis-bit", "DISMISSED")]

    assert build_one(pull, detail, GREEN, reviews).approvals == 0


def test_approvals_count_reviewers_not_reviews(pull, detail):
    reviews = [
        review("GustaReis-bit", "APPROVED"),
        review("gustareis-bit", "APPROVED"),  # mesma pessoa
        review("DrawnGZN", "APPROVED"),
        review("outro", "CHANGES_REQUESTED"),
    ]

    assert build_one(pull, detail, GREEN, reviews).approvals == 2


# ------------------------------------------------------- canApprove/canMerge


def test_cannot_approve_own_pull(pull, detail):
    item = build_one(pull, detail, GREEN, token_login="ALV4ROSO4RES")

    assert item.can_approve is False


def test_cannot_approve_draft(pull, detail):
    assert build_one(pull, detail, GREEN, draft=True).can_approve is False


def test_cannot_approve_with_write_disabled(pull, detail):
    item = build_one(pull, detail, GREEN, write_enabled=False)

    assert item.can_approve is False


def test_cannot_approve_without_token_login(pull, detail):
    assert build_one(pull, detail, GREEN, token_login=None).can_approve is False


def test_cannot_approve_when_already_approved(pull, detail):
    reviews = [review("Dono-Do-Token", "APPROVED"), review("dono-do-token", "COMMENTED")]

    assert build_one(pull, detail, GREEN, reviews).can_approve is False


def test_can_approve_again_after_requesting_changes(pull, detail):
    reviews = [review(TOKEN_LOGIN, "APPROVED"), review(TOKEN_LOGIN, "CHANGES_REQUESTED")]

    assert build_one(pull, detail, GREEN, reviews).can_approve is True


def test_cannot_merge_with_write_disabled(pull, detail):
    item = build_one(pull, detail, GREEN, write_enabled=False, mergeable_state="clean")

    assert item.can_merge is False


def test_can_merge_even_when_blocked(pull, detail):
    item = build_one(pull, detail, [check("failure")], mergeable_state="dirty")

    assert item.can_merge is True


# --------------------------------------------------------------- imutáveis


def test_build_pulls_does_not_mutate_input(pull, detail, checks, reviews):
    args = ([pull], {NUMBER: detail}, {NUMBER: checks}, {NUMBER: reviews})
    before = copy.deepcopy(args)

    build_pulls(*args, token_login=TOKEN_LOGIN, write_enabled=True)

    assert args == before
