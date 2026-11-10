from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.schemas.common import ApiModel, RunStatus


class Exemplo(ApiModel):
    head_sha: str
    run_status: RunStatus
    created_at: datetime


DADOS = {
    "head_sha": "abc1234",
    "run_status": "in_progress",
    "created_at": datetime(2026, 11, 10, 12, 30, tzinfo=UTC),
}


def test_model_dump_is_camel_case():
    dumped = Exemplo(**DADOS).model_dump()

    assert set(dumped) == {"headSha", "runStatus", "createdAt"}


def test_accepts_snake_case_name():
    modelo = Exemplo.model_validate(DADOS)

    assert modelo.head_sha == "abc1234"
    assert modelo.run_status is RunStatus.IN_PROGRESS


def test_accepts_camel_case_alias():
    modelo = Exemplo.model_validate(
        {
            "headSha": "abc1234",
            "runStatus": "success",
            "createdAt": "2026-11-10T12:30:00Z",
        }
    )

    assert modelo.head_sha == "abc1234"
    assert modelo.run_status is RunStatus.SUCCESS
    assert modelo.created_at == DADOS["created_at"]


def test_route_with_response_model_returns_camel_case_json():
    app = FastAPI()

    @app.get("/exemplo", response_model=Exemplo)
    def exemplo() -> Exemplo:
        return Exemplo(**DADOS)

    with TestClient(app) as client:
        response = client.get("/exemplo")

    assert response.status_code == 200
    assert response.json() == {
        "headSha": "abc1234",
        "runStatus": "in_progress",
        "createdAt": "2026-11-10T12:30:00Z",
    }
