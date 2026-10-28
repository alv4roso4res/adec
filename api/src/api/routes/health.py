from typing import Annotated

from fastapi import APIRouter, Depends

from api.config import Settings
from api.deps import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, str]:
    return {"status": "ok", "version": settings.app_version}
