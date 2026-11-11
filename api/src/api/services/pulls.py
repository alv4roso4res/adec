"""Monta o card 3: PRs abertos com checks, aprovações e badge.

Função pura: recebe os dicts crus do GitHub (lista de PRs e, indexados pelo
número do PR, detalhes, check runs e reviews); não faz requisição e nunca
altera o que recebe (o cache do GitHubClient devolve o mesmo objeto).
"""

from collections.abc import Mapping, Sequence
from typing import Any

from api.schemas.common import RunStatus
from api.schemas.pulls import PullAuthor, PullBadge, PullChecks, PullItem
from api.services.pipeline import normalize_status

Raw = Mapping[str, Any]

# Reviews que não mudam a decisão do revisor. PENDING é um review ainda não
# enviado (só o próprio autor dele o vê).
_IGNORED_REVIEW_STATES = {"COMMENTED", "PENDING"}
_READY_STATES = {"clean", "unstable", "has_hooks"}


def build_pulls(
    pulls: Sequence[Raw],
    details: Mapping[int, Raw],
    check_runs: Mapping[int, Sequence[Raw]],
    reviews: Mapping[int, Sequence[Raw]],
    token_login: str | None,
    write_enabled: bool,
) -> list[PullItem]:
    """PRs na ordem recebida (a do GitHub: mais novo primeiro)."""
    return [
        _to_item(
            pull,
            details.get(pull["number"], {}),
            check_runs.get(pull["number"], []),
            reviews.get(pull["number"], []),
            token_login,
            write_enabled,
        )
        for pull in pulls
    ]


def count_checks(check_runs: Sequence[Raw]) -> PullChecks:
    """Conta os checks; `skipped`/`neutral` não entram em nenhuma contagem."""
    passed = failed = pending = 0
    for run in check_runs:
        if run.get("status") != "completed":
            pending += 1
            continue
        status = normalize_status("completed", run.get("conclusion"))
        if status is RunStatus.SUCCESS:
            passed += 1
        elif status is not RunStatus.SKIPPED:
            # failure, cancelled, timed_out, action_required...
            failed += 1
    return PullChecks(passed=passed, failed=failed, pending=pending)


def latest_decisions(reviews: Sequence[Raw]) -> dict[str, str]:
    """Último review de cada revisor (login em minúsculas → state), ignorando
    comentários. Os reviews do GitHub vêm em ordem cronológica."""
    decisions: dict[str, str] = {}
    for review in reviews:
        login = (review.get("user") or {}).get("login")
        state = review.get("state")
        if login and state and state not in _IGNORED_REVIEW_STATES:
            decisions[login.lower()] = state
    return decisions


def pick_badge(detail: Raw, checks: PullChecks) -> PullBadge:
    """Badge de maior prioridade (ver PullBadge)."""
    state = detail.get("mergeable_state")
    if detail.get("draft"):
        return PullBadge.DRAFT
    if state == "dirty":
        return PullBadge.CONFLICT
    if checks.failed:
        return PullBadge.CHECKS_FAILED
    if checks.pending or not checks.passed:
        return PullBadge.WAITING_CHECKS
    if state == "blocked":
        return PullBadge.NEEDS_APPROVAL
    if state in _READY_STATES:
        return PullBadge.READY
    # "unknown", null ou qualquer valor que o GitHub venha a inventar.
    return PullBadge.COMPUTING


def _to_item(
    pull: Raw,
    detail: Raw,
    check_runs: Sequence[Raw],
    reviews: Sequence[Raw],
    token_login: str | None,
    write_enabled: bool,
) -> PullItem:
    author = pull.get("user") or {}
    checks = count_checks(check_runs)
    decisions = latest_decisions(reviews)
    badge = pick_badge(detail, checks)

    is_own = bool(token_login) and (author.get("login") or "").lower() == token_login.lower()
    already_approved = bool(token_login) and decisions.get(token_login.lower()) == "APPROVED"
    can_approve = (
        write_enabled
        and bool(token_login)
        and not is_own
        and not detail.get("draft")
        and not already_approved
    )

    return PullItem(
        number=pull["number"],
        title=pull["title"],
        author=PullAuthor(login=author["login"], avatar_url=author["avatar_url"]),
        created_at=pull["created_at"],
        html_url=pull["html_url"],
        head_sha=pull["head"]["sha"],
        checks=checks,
        approvals=sum(state == "APPROVED" for state in decisions.values()),
        badge=badge,
        can_approve=can_approve,
        can_merge=write_enabled,
    )
