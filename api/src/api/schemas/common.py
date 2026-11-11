"""Base comum dos schemas de resposta da API.

Convenções:
- O código Python usa snake_case; o JSON sai sempre em camelCase.
- Datas são sempre timezone-aware em UTC e serializadas em ISO 8601.
  O frontend é quem formata a exibição ("há X min").
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        # Aceita tanto `head_sha` quanto `headSha` na validação...
        validate_by_name=True,
        validate_by_alias=True,
        # ...e serializa sempre em camelCase (model_dump e response_model).
        serialize_by_alias=True,
    )


class RunStatus(StrEnum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"
    # Job que não rodou (ex.: deploy quando o build-test falha).
    SKIPPED = "skipped"
