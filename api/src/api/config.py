import json
from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    github_token: str = ""
    github_owner: str = ""
    github_repo: str = ""
    # NoDecode: sem isso o pydantic-settings exigiria JSON ('["a","b"]') e
    # quebraria com TEAM_LOGINS vazio. Aceita "a,b" ou JSON (ver validador).
    team_logins: Annotated[list[str], NoDecode] = []
    ghcr_package: str = ""
    app_version: str = "dev"
    enable_write_actions: bool = False
    cache_ttl_seconds: int = 15

    @field_validator("team_logins", mode="before")
    @classmethod
    def _split_team_logins(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("["):
                return json.loads(value)
            return [login.strip() for login in value.split(",") if login.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
