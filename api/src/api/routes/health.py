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
        "Confirma que a API está de pé e informa a versão em execução. Não fala "
        "com o GitHub. Usado pelo healthcheck da imagem Docker da API."
    ),
    response_description="API no ar e versão em execução.",
)
def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    return HealthResponse(status="ok", version=settings.app_version)
