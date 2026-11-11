import json
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

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


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "github"


@pytest.fixture
def github_fixture() -> Callable[[str], Any]:
    """Carrega um JSON real do GitHub salvo em tests/fixtures/github/.

    Cada chamada lê o arquivo de novo, então o teste pode alterar o resultado
    à vontade para derivar variações (in_progress, cancelled...).
    """

    def load(name: str) -> Any:
        return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))

    return load
