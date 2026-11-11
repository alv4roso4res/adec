import copy

import pytest

from api.services.team import build_team

# Fixtures reais: alv4roso4res tem 9 PRs mergeados e 15 commits; GustaReis-bit,
# 1 PR mergeado e 8 commits; DrawnGZN ainda não tem atividade nenhuma.
TEAM = ["alv4roso4res", "GustaReis-bit", "DrawnGZN"]
AVATAR_GUSTA = "https://avatars.githubusercontent.com/u/200959764?v=4"


@pytest.fixture
def pulls(github_fixture) -> list[dict]:
    return github_fixture("pulls_all.json")


@pytest.fixture
def contributors(github_fixture) -> list[dict]:
    return github_fixture("contributors.json")


def make_pull(login: str, state: str, merged_at: str | None = None, **user) -> dict:
    return {
        "number": 99,
        "title": "PR de teste",
        "state": state,
        "merged_at": merged_at,
        "user": {"login": login, "avatar_url": f"https://avatars.example/{login}"} | user,
    }


def by_login(members) -> dict:
    return {m.login: m for m in members}


def test_build_team_from_real_fixtures(pulls, contributors):
    members = build_team(TEAM, pulls, contributors)

    assert [
        (m.login, m.prs_open, m.prs_merged, m.commits, m.meets_requirement)
        for m in members
    ] == [
        ("alv4roso4res", 0, 9, 15, True),
        ("GustaReis-bit", 0, 1, 8, True),
        ("DrawnGZN", 0, 0, 0, False),
    ]
    assert members[1].avatar_url == AVATAR_GUSTA


def test_member_without_activity_has_zeros_and_fallback_avatar(pulls, contributors):
    idle = build_team(["DrawnGZN"], pulls, contributors)[0]

    assert idle.login == "DrawnGZN"
    assert idle.avatar_url == "https://github.com/DrawnGZN.png"
    assert (idle.prs_open, idle.prs_merged, idle.commits) == (0, 0, 0)
    assert idle.meets_requirement is False


def test_login_matches_ignoring_case(pulls, contributors):
    member = build_team(["gustareis-BIT"], pulls, contributors)[0]

    # Sai como o GitHub devolve, não como foi configurado.
    assert member.login == "GustaReis-bit"
    assert member.commits == 8
    assert member.prs_merged == 1


def test_order_follows_team_logins(pulls, contributors):
    order = ["DrawnGZN", "GustaReis-bit", "alv4roso4res"]

    assert [m.login for m in build_team(order, pulls, contributors)] == order


def test_open_merged_and_closed_without_merge_are_counted(contributors):
    pulls = [
        make_pull("DrawnGZN", "open"),
        make_pull("DrawnGZN", "open"),
        make_pull("DrawnGZN", "closed", merged_at="2026-11-11T02:34:03Z"),
        make_pull("DrawnGZN", "closed"),  # fechado sem merge
    ]

    member = build_team(["DrawnGZN"], pulls, contributors)[0]

    assert member.prs_open == 2
    assert member.prs_merged == 1
    assert member.meets_requirement is True


def test_only_closed_without_merge_meets_requirement(contributors):
    member = build_team(["DrawnGZN"], [make_pull("DrawnGZN", "closed")], contributors)[0]

    assert (member.prs_open, member.prs_merged) == (0, 0)
    assert member.meets_requirement is True


def test_avatar_from_pull_author_when_not_a_contributor(contributors):
    # Abriu PR mas ainda não tem commit na branch padrão.
    member = build_team(["drawngzn"], [make_pull("DrawnGZN", "open")], contributors)[0]

    assert member.login == "DrawnGZN"
    assert member.avatar_url == "https://avatars.example/DrawnGZN"
    assert member.commits == 0


def test_people_outside_the_team_are_ignored(pulls, contributors):
    pulls = [*pulls, make_pull("dependabot[bot]", "open"), make_pull("externo", "open")]
    contributors = [*contributors, {"login": "externo", "contributions": 50}]

    members = build_team(TEAM, pulls, contributors)

    assert [m.login for m in members] == TEAM
    assert sum(m.prs_open for m in members) == 0


def test_contributor_without_login_is_ignored(pulls, contributors):
    # /contributors?anon=1 traz entradas sem login (e-mail sem conta).
    contributors = [*contributors, {"type": "Anonymous", "contributions": 3}]

    assert build_team(["DrawnGZN"], pulls, contributors)[0].commits == 0


def test_empty_team_logins(pulls, contributors):
    assert build_team([], pulls, contributors) == []


def test_build_team_does_not_mutate_input(pulls, contributors):
    team = list(TEAM)
    before = copy.deepcopy((team, pulls, contributors))

    build_team(team, pulls, contributors)

    assert (team, pulls, contributors) == before
