import httpx
from fastapi import HTTPException, Request

from api.config import Settings
from api.github.client import GitHubClient


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


def get_github_client(request: Request) -> GitHubClient:
    return request.app.state.github_client


WRITE_ACTIONS_DISABLED = "Ações de escrita estão desligadas"


def require_write_actions(request: Request) -> None:
    """Barra as rotas de escrita com 403 quando ENABLE_WRITE_ACTIONS=false,
    antes de qualquer chamada ao GitHub."""
    if not get_settings(request).enable_write_actions:
        raise HTTPException(status_code=403, detail=WRITE_ACTIONS_DISABLED)
