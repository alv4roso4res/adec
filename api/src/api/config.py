import json
from functools import lru_cache
from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator
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
    github_workflow_file: str = "ci.yml"
    # NoDecode: sem isso o pydantic-settings exigiria JSON ('["a","b"]') e
    # quebraria com a variável vazia. Aceita "a,b" ou JSON (ver validador).
    team_logins: Annotated[list[str], NoDecode] = []
    ghcr_images: Annotated[list[str], NoDecode] = ["adec-api", "adec-frontend"]
    # Vazio = usa github_owner. Sempre em minúsculas (o GHCR exige).
    ghcr_owner: str = ""
    app_version: str = "dev"
    enable_write_actions: bool = False
    merge_method: Literal["merge", "squash"] = "merge"
    pulls_limit: int = Field(default=5, ge=1)
    history_limit: int = Field(default=20, ge=1)

    @field_validator("team_logins", "ghcr_images", mode="before")
    @classmethod
    def _split_list(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("["):
                return json.loads(value)
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def _resolve_ghcr_owner(self) -> Self:
        self.ghcr_owner = (self.ghcr_owner or self.github_owner).lower()
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
