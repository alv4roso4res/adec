import pytest

from api.config import Settings


def test_defaults():
    settings = Settings(_env_file=None)

    assert settings.team_logins == []
    assert settings.app_version == "dev"
    assert settings.enable_write_actions is False
    assert settings.cache_ttl_seconds == 15


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("", []),
        ("ana", ["ana"]),
        ("ana, bia ,caio", ["ana", "bia", "caio"]),
        ('["ana","bia"]', ["ana", "bia"]),
    ],
)
def test_team_logins_from_env(monkeypatch, raw, expected):
    monkeypatch.setenv("TEAM_LOGINS", raw)

    assert Settings(_env_file=None).team_logins == expected
