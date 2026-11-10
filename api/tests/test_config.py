import pytest
from pydantic import ValidationError

from api.config import Settings


def test_defaults():
    settings = Settings(_env_file=None)

    assert settings.team_logins == []
    assert settings.ghcr_images == ["adec-api", "adec-frontend"]
    assert settings.ghcr_owner == ""
    assert settings.github_workflow_file == "ci.yml"
    assert settings.app_version == "dev"
    assert settings.enable_write_actions is False
    assert settings.merge_method == "merge"
    assert settings.pulls_limit == 5
    assert settings.history_limit == 20


LIST_CASES = [
    ("", []),
    ("ana", ["ana"]),
    ("ana, bia ,caio", ["ana", "bia", "caio"]),
    ('["ana","bia"]', ["ana", "bia"]),
]


@pytest.mark.parametrize(("raw", "expected"), LIST_CASES)
def test_team_logins_from_env(monkeypatch, raw, expected):
    monkeypatch.setenv("TEAM_LOGINS", raw)

    assert Settings(_env_file=None).team_logins == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("", []),
        ("adec-api", ["adec-api"]),
        ("adec-api, adec-frontend", ["adec-api", "adec-frontend"]),
        ('["adec-api","adec-frontend"]', ["adec-api", "adec-frontend"]),
    ],
)
def test_ghcr_images_from_env(monkeypatch, raw, expected):
    monkeypatch.setenv("GHCR_IMAGES", raw)

    assert Settings(_env_file=None).ghcr_images == expected


def test_ghcr_owner_falls_back_to_github_owner_in_lowercase():
    settings = Settings(_env_file=None, github_owner="Alv4roSo4res")

    assert settings.ghcr_owner == "alv4roso4res"
    # O github_owner original não é alterado.
    assert settings.github_owner == "Alv4roSo4res"


def test_explicit_ghcr_owner_wins_and_is_lowercased():
    settings = Settings(_env_file=None, github_owner="alguem", ghcr_owner="Org-ADEC")

    assert settings.ghcr_owner == "org-adec"


def test_ghcr_owner_from_env(monkeypatch):
    monkeypatch.setenv("GITHUB_OWNER", "Alguem")
    monkeypatch.setenv("GHCR_OWNER", "OutroDono")

    assert Settings(_env_file=None).ghcr_owner == "outrodono"


def test_invalid_merge_method_raises():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, merge_method="rebase")


@pytest.mark.parametrize("field", ["pulls_limit", "history_limit"])
def test_limits_must_be_at_least_one(field):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: 0})
