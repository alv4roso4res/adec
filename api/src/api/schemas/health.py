"""Resposta do health check."""

from pydantic import ConfigDict, Field

from api.schemas.common import ApiModel


class HealthResponse(ApiModel):
    """Indica que a API está de pé e qual versão está rodando."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"status": "ok", "version": "5ef3733"}]}
    )

    status: str = Field(
        description='Sempre "ok" quando a API responde.',
        examples=["ok"],
    )
    version: str = Field(
        description=(
            "Versão em execução (APP_VERSION): o SHA curto embutido na imagem, "
            'ou "dev" fora do Docker.'
        ),
        examples=["5ef3733", "dev"],
    )
