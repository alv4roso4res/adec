"""Trava a convenção de documentação da API (Swagger em /api/docs).

Toda rota nova precisa de summary, description, operation_id e (se falar com
o GitHub) das respostas 502/503; todo campo de schema precisa de description e
estar em camelCase. Cada teste lista exatamente o que está faltando.
"""

import re
from typing import Any

import pytest
from fastapi.routing import APIRoute

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
# Schemas gerados pelo próprio FastAPI (erro 422), fora do nosso controle.
FASTAPI_SCHEMAS = {"HTTPValidationError", "ValidationError"}
# Tags de rotas que não falam com o GitHub.
TAGS_WITHOUT_GITHUB = {"health"}
SNAKE_CASE = re.compile(r"[a-z][a-z0-9_]*")


@pytest.fixture
def spec(app) -> dict[str, Any]:
    return app.openapi()


def operations(spec: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    return [
        (f"{method.upper()} {path}", op)
        for path, item in spec["paths"].items()
        for method, op in item.items()
        if method in HTTP_METHODS
    ]


def our_schemas(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    schemas = spec.get("components", {}).get("schemas", {})
    return {n: s for n, s in schemas.items() if n not in FASTAPI_SCHEMAS}


def assert_none_missing(missing: list[str], what: str) -> None:
    assert not missing, f"{what}:\n  " + "\n  ".join(missing)


def test_spec_is_served_under_api(client):
    response = client.get("/api/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "ADEC — API do painel de CI/CD"


def test_info_has_title_version_and_description(spec, settings):
    info = spec["info"]

    assert info["title"] == "ADEC — API do painel de CI/CD"
    assert info["version"] == settings.app_version
    assert info.get("description", "").strip(), "info.description está vazia"


def test_every_used_tag_has_description(spec):
    described = {t["name"] for t in spec.get("tags", []) if t.get("description")}
    used = {tag for _, op in operations(spec) for tag in op.get("tags", [])}

    assert_none_missing(
        sorted(used - described), "Tags usadas sem descrição em openapi_tags"
    )


def test_every_operation_has_a_tag(spec):
    missing = [name for name, op in operations(spec) if not op.get("tags")]

    assert_none_missing(missing, "Rotas sem tag")


def test_every_operation_has_description(spec):
    missing = [name for name, op in operations(spec) if not op.get("description")]

    assert_none_missing(missing, "Rotas sem description")


@pytest.mark.parametrize("attr", ["summary", "operation_id"])
def test_every_route_sets_explicitly(app, attr):
    # O FastAPI inventa summary e operationId a partir do nome da função, então
    # o spec sempre os tem; aqui conferimos o que foi passado no decorator.
    missing = [
        f"{','.join(sorted(route.methods))} {route.path}"
        for route in app.routes
        if isinstance(route, APIRoute)
        and route.include_in_schema
        and not getattr(route, attr)
    ]

    assert_none_missing(missing, f"Rotas sem {attr}= no decorator")


def test_operation_ids_are_snake_case(spec):
    bad = [
        f"{name}: {op['operationId']}"
        for name, op in operations(spec)
        if op.get("operationId") and not SNAKE_CASE.fullmatch(op["operationId"])
    ]

    assert_none_missing(bad, "operation_id fora de snake_case")


def test_github_routes_document_502_and_503(spec):
    missing = [
        f"{name} sem {status}"
        for name, op in operations(spec)
        if not set(op.get("tags", [])) <= TAGS_WITHOUT_GITHUB
        for status in ("502", "503")
        if status not in op.get("responses", {})
    ]

    assert_none_missing(
        missing, "Rotas que falam com o GitHub sem responses=GITHUB_ERROR_RESPONSES"
    )


def test_every_parameter_has_description(spec):
    missing = [
        f"{name} → parâmetro {param['name']}"
        for name, op in operations(spec)
        for param in op.get("parameters", [])
        if not param.get("description")
    ]

    assert_none_missing(missing, "Parâmetros sem description")


def test_every_schema_has_description(spec):
    missing = [name for name, s in our_schemas(spec).items() if not s.get("description")]

    assert_none_missing(missing, "Schemas sem docstring")


def test_every_schema_property_has_description(spec):
    missing = [
        f"{schema}.{prop}"
        for schema, s in our_schemas(spec).items()
        for prop, definition in s.get("properties", {}).items()
        if not definition.get("description")
    ]

    assert_none_missing(missing, "Campos sem Field(description=...)")


def test_schema_properties_are_camel_case(spec):
    bad = [
        f"{schema}.{prop}"
        for schema, s in our_schemas(spec).items()
        for prop in s.get("properties", {})
        if "_" in prop
    ]

    assert_none_missing(bad, "Campos fora de camelCase (use ApiModel)")
