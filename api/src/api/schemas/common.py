"""Base comum dos schemas de resposta da API.

Convenções:
- O código Python usa snake_case; o JSON sai sempre em camelCase.
- Datas são sempre timezone-aware em UTC e serializadas em ISO 8601.
  O frontend é quem formata a exibição ("há X min").
- Todo campo tem Field(description=..., examples=[...]) e todo modelo tem
  docstring: é isso que aparece no Swagger (/api/docs). O teste
  tests/test_openapi.py reprova campo sem descrição.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    """Base de todas as respostas: JSON em camelCase."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        # Aceita tanto `head_sha` quanto `headSha` na validação...
        validate_by_name=True,
        validate_by_alias=True,
        # ...e serializa sempre em camelCase (model_dump e response_model).
        serialize_by_alias=True,
    )


class RunStatus(StrEnum):
    """Status normalizado de um run, job ou step do GitHub Actions.

    Junta `status` + `conclusion` do GitHub num valor só:

    - `queued`: na fila (queued, waiting, requested ou pending);
    - `in_progress`: rodando agora;
    - `success`: concluído com sucesso;
    - `failure`: concluído com falha (failure, timed_out, action_required,
      startup_failure, stale ou qualquer conclusão desconhecida);
    - `cancelled`: cancelado antes de terminar;
    - `skipped`: não rodou (skipped ou neutral), por exemplo o job `deploy`
      quando o `build-test` falha.
    """

    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"
    # Job que não rodou (ex.: deploy quando o build-test falha).
    SKIPPED = "skipped"


class ErrorResponse(ApiModel):
    """Formato de todo erro da API (inclusive os traduzidos do GitHub)."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"detail": "API rate limit exceeded"}]}
    )

    detail: str = Field(
        description="Mensagem do erro, legível por pessoas.",
        examples=["API rate limit exceeded", "Não foi possível falar com o GitHub"],
    )
