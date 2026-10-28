from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from api.config import Settings
from api.main import create_app


@pytest.fixture
def settings() -> Settings:
    # _env_file=None: o teste não pode depender do .env local de quem roda.
    return Settings(
        _env_file=None,
        github_token="token-de-teste",
        github_owner="owner-teste",
        github_repo="repo-teste",
        app_version="1.2.3-test",
    )


@pytest.fixture
def app(settings: Settings):
    return create_app(settings)


@pytest.fixture
def client(app) -> Iterator[TestClient]:
    # `with` é o que dispara o lifespan (cria/fecha o httpx.AsyncClient).
    with TestClient(app) as test_client:
        yield test_client
