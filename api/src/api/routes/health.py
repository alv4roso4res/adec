from typing import Annotated

from fastapi import APIRouter, Depends

from api.config import Settings
from api.deps import get_settings
from api.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    operation_id="get_health",
    summary="Saúde da API",
    description=(
        "Confirma que a API está de pé e informa a versão em execução, o "
        "repositório monitorado e se as ações de escrita estão ligadas "
        "(metadados do cabeçalho do painel). Não fala com o GitHub. Usado "
        "pelo healthcheck da imagem Docker da API."
    ),
    response_description="API no ar, versão em execução e metadados do painel.",
)
def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        repository=f"{settings.github_owner}/{settings.github_repo}",
        write_actions_enabled=settings.enable_write_actions,
    )
