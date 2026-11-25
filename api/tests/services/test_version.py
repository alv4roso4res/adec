import copy

import pytest

from api.schemas.version import VersionState
from api.services.version import build_version, published_sha, same_sha

# Fixtures reais: a main (commits.json) e a imagem mais nova das duas
# (package_versions_*.json) estão em e8eb3e0. O merge seguinte, 092ded1, é
# usado para simular "main andou e o pipeline ainda não publicou".
MAIN = "e8eb3e0aa85bb8e7c0af9c52ae69197d024e941c"
NEW_MAIN = "092ded138f40aa42072bd8a05eaabe7bc9f7202a"
OLD = "3d4833f"  # versão publicada antes de e8eb3e0
IMAGES = ("adec-api", "adec-frontend")


@pytest.fixture
def commits(github_fixture) -> list[dict]:
    return github_fixture("commits.json")


@pytest.fixture
def packages(github_fixture) -> dict[str, list[dict]]:
    return {img: github_fixture(f"package_versions_{img}.json") for img in IMAGES}


def new_main(commits: list[dict]) -> list[dict]:
    """A main ganhou um commit novo (092ded1) em cima das fixtures."""
    return [{"sha": NEW_MAIN, "commit": {"message": "Merge pull request #9"}}, *commits]


def push_run(sha: str, status: str, conclusion: str | None = None, **extra) -> dict:
    return {
        "head_sha": sha,
        "event": "push",
        "status": status,
        "conclusion": conclusion,
        "created_at": "2026-11-11T02:19:34Z",
    } | extra


def publish(versions: list[dict], short_sha: str) -> list[dict]:
    """Simula o deploy: o GHCR ganha uma versão nova com só a tag sha-xxx."""
    new = {
        "id": 1,
        "created_at": "2026-11-11T02:30:00Z",
        "metadata": {"container": {"tags": [f"sha-{short_sha}"]}},
    }
    return [new, *copy.deepcopy(versions)]


# --------------------------------------------------------------- same_sha


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ("e8eb3e0", MAIN, True),  # 7 chars do Actions × SHA completo
        (MAIN, "e8eb3e0", True),
        ("e8eb3e0aa8", "e8eb3e0", True),  # rev-parse --short com mais chars
        ("E8EB3E0", MAIN, True),
        ("e8eb3e0", "e8eb3e1", False),
        ("3d4833f", MAIN, False),
        ("e8eb3e", MAIN, False),  # curto demais: não casa com qualquer coisa
        (None, MAIN, False),
        ("e8eb3e0", None, False),
        ("", "", False),
    ],
)
def test_same_sha_compares_by_prefix(a, b, expected):
    assert same_sha(a, b) is expected


# ---------------------------------------------------------- published_sha


def test_published_sha_from_real_fixture(packages):
    assert published_sha(packages["adec-api"]) == "e8eb3e0"
    assert published_sha(packages["adec-frontend"]) == "e8eb3e0"


def test_published_sha_is_the_newest_sha_tag(packages):
    # Sem a versão mais nova (e8eb3e0), vale a anterior com tag sha-.
    older = packages["adec-api"][1:]

    assert published_sha(older) == OLD
    assert published_sha(publish(packages["adec-api"], "092ded1")) == "092ded1"


def test_published_sha_uses_created_at_not_list_order():
    versions = [
        {"created_at": "2026-11-10T10:00:00Z", "metadata": {"container": {"tags": ["sha-aaaaaaa"]}}},
        {"created_at": "2026-11-11T10:00:00Z", "metadata": {"container": {"tags": ["sha-bbbbbbb"]}}},
    ]

    assert published_sha(versions) == "bbbbbbb"


def test_published_sha_ignores_versions_without_sha_tag():
    versions = [
        {"created_at": "2026-11-11T10:00:00Z", "metadata": {"container": {"tags": ["latest"]}}},
        {"created_at": "2026-11-11T10:00:00Z", "metadata": {"container": {"tags": []}}},
    ]

    assert published_sha(versions) is None
    assert published_sha([]) is None


# ---------------------------------------------------------- os 5 estados


@pytest.mark.parametrize("running", ["dev", "check-local", "1.2.3-test"])
def test_state_dev_when_running_is_not_a_sha(running, commits, packages):
    info = build_version(running, commits, [], packages)

    assert info.state is VersionState.DEV
    # Mesmo em dev o card mostra main e imagens.
    assert info.main_sha == MAIN
    assert [i.published_sha for i in info.images] == ["e8eb3e0", "e8eb3e0"]


@pytest.mark.parametrize("running", ["e8eb3e0", "e8eb3e0aa85", "E8EB3E0"])
def test_state_up_to_date(running, commits, packages):
    info = build_version(running, commits, [], packages)

    assert info.state is VersionState.UP_TO_DATE
    assert info.running == running
    assert info.main_sha == MAIN
    assert [(i.name, i.published_sha) for i in info.images] == [
        ("adec-api", "e8eb3e0"),
        ("adec-frontend", "e8eb3e0"),
    ]


def test_state_restart_pending(commits, packages):
    # A imagem mais nova já é a main, mas o container ainda roda a anterior.
    info = build_version(OLD, commits, [], packages)

    assert info.state is VersionState.RESTART_PENDING


@pytest.mark.parametrize("status", ["queued", "in_progress"])
def test_state_building_while_main_pipeline_runs(status, commits, packages):
    info = build_version("e8eb3e0", new_main(commits), [push_run(NEW_MAIN, status)], packages)

    assert info.state is VersionState.BUILDING
    assert info.main_sha == NEW_MAIN


def test_state_building_when_run_not_created_yet(commits, packages):
    # Merge de segundos atrás: o run de push da main ainda não apareceu.
    runs = [push_run(MAIN, "completed", "success")]

    info = build_version("e8eb3e0", new_main(commits), runs, packages)

    assert info.state is VersionState.BUILDING


def test_state_building_when_run_succeeded_but_image_still_old(commits, packages):
    # Run acabou, mas o GHCR (cache de 30 s) ainda mostra a imagem anterior.
    runs = [push_run(NEW_MAIN, "completed", "success")]

    info = build_version("e8eb3e0", new_main(commits), runs, packages)

    assert info.state is VersionState.BUILDING


@pytest.mark.parametrize("conclusion", ["failure", "cancelled", "timed_out"])
def test_state_pipeline_failed(conclusion, commits, packages):
    runs = [push_run(NEW_MAIN, "completed", conclusion)]

    info = build_version("e8eb3e0", new_main(commits), runs, packages)

    assert info.state is VersionState.PIPELINE_FAILED


def test_pull_request_run_does_not_decide_state(commits, packages):
    # Só o run de push publica; um PR vermelho no mesmo SHA não é "pipeline falhou".
    runs = [push_run(NEW_MAIN, "completed", "failure", event="pull_request")]

    info = build_version("e8eb3e0", new_main(commits), runs, packages)

    assert info.state is VersionState.BUILDING


def test_latest_push_run_wins_on_rerun(commits, packages):
    # Run falhou e foi re-executado; o re-run (mais recente) está rodando.
    runs = [
        push_run(NEW_MAIN, "in_progress", created_at="2026-11-11T02:30:00Z"),
        push_run(NEW_MAIN, "completed", "failure", created_at="2026-11-11T02:19:34Z"),
    ]

    for ordered in (runs, runs[::-1]):
        info = build_version("e8eb3e0", new_main(commits), ordered, packages)
        assert info.state is VersionState.BUILDING


# ------------------------------------------ imagens divergentes (API × front)


def test_divergent_images_mid_deploy_is_building(commits, packages):
    # O deploy publica uma imagem por vez: a API já saiu, o frontend ainda não.
    diverged = packages | {"adec-api": publish(packages["adec-api"], "092ded1")}
    runs = [push_run(NEW_MAIN, "in_progress")]

    info = build_version("e8eb3e0", new_main(commits), runs, diverged)

    assert [(i.name, i.published_sha) for i in info.images] == [
        ("adec-api", "092ded1"),
        ("adec-frontend", "e8eb3e0"),
    ]
    assert info.state is VersionState.BUILDING


def test_divergent_images_never_count_as_published(commits, packages):
    # Mesmo rodando a main, só uma imagem publicada não é up_to_date nem restart.
    diverged = packages | {"adec-api": publish(packages["adec-api"], "092ded1")}
    runs = [push_run(NEW_MAIN, "completed", "success")]

    for running in ("092ded1", "e8eb3e0"):
        info = build_version(running, new_main(commits), runs, diverged)
        assert info.state is VersionState.BUILDING


def test_divergent_images_after_failed_deploy(commits, packages):
    # A segunda publicação falhou: o run fica vermelho e as imagens divergem.
    diverged = packages | {"adec-api": publish(packages["adec-api"], "092ded1")}
    runs = [push_run(NEW_MAIN, "completed", "failure")]

    info = build_version("e8eb3e0", new_main(commits), runs, diverged)

    assert info.state is VersionState.PIPELINE_FAILED


def test_both_images_published_is_restart_pending(commits, packages):
    published = {img: publish(packages[img], "092ded1") for img in IMAGES}
    runs = [push_run(NEW_MAIN, "completed", "success")]

    assert (
        build_version("e8eb3e0", new_main(commits), runs, published).state
        is VersionState.RESTART_PENDING
    )
    assert (
        build_version("092ded1", new_main(commits), runs, published).state
        is VersionState.UP_TO_DATE
    )


# ------------------------------------------------------------ bordas


def test_image_not_published_yet(commits, packages):
    info = build_version("e8eb3e0", commits, [], packages | {"adec-frontend": []})

    assert info.images[1].published_sha is None
    assert info.state is VersionState.BUILDING


def test_no_images_configured_is_not_up_to_date(commits):
    info = build_version("e8eb3e0", commits, [], {})

    assert info.images == []
    assert info.state is VersionState.BUILDING


def test_empty_main(packages):
    info = build_version("e8eb3e0", [], [], packages)

    assert info.main_sha is None
    assert info.state is VersionState.BUILDING


def test_build_version_does_not_mutate_input(commits, packages):
    runs = [push_run(NEW_MAIN, "in_progress")]
    main = new_main(commits)
    before = copy.deepcopy((main, runs, packages))

    build_version("e8eb3e0", main, runs, packages)

    assert (main, runs, packages) == before
