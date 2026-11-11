"""Resposta do health check."""

from pydantic import ConfigDict, Field

from api.schemas.common import ApiModel


class HealthResponse(ApiModel):
    """Indica que a API está de pé, qual versão está rodando e os metadados
    do cabeçalho do painel (repositório monitorado e se a escrita está ligada)."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{
                    "status": "ok",
                    "version": "5ef3733",
                    "repository": "alv4roso4res/adec",
                    "writeActionsEnabled": True,
                }]}
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
    repository: str = Field(
        description='Repositório monitorado, "owner/repo" (GITHUB_OWNER/GITHUB_REPO).',
        examples=["alv4roso4res/adec"],
    )
    write_actions_enabled: bool = Field(
        description=(
            "ENABLE_WRITE_ACTIONS: true se o painel pode aprovar/mergear PRs "
            "(senão os botões ficam desligados e as rotas devolvem 403)."
        ),
        examples=[True],
    )
