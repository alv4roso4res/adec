import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends

from api.config import Settings
from api.deps import get_github_client, get_settings
from api.errors import GITHUB_ERROR_RESPONSES
from api.github.client import GitHubClient
from api.schemas.team import TeamMember
from api.services.team import build_team

router = APIRouter(prefix="/team", tags=["team"])

# Máximo do GitHub por página: cobre todos os PRs de um trabalho de semestre.
PULLS_PER_PAGE = 100


@router.get(
    "",
    response_model=list[TeamMember],
    responses=GITHUB_ERROR_RESPONSES,
    operation_id="get_team",
    summary="Integrantes do time",
    description=(
        "**Card 4 (integrantes).** Um item por login de `TEAM_LOGINS`, na ordem "
        "configurada, com PRs abertos e mergeados, commits na branch padrão e "
        "`meetsRequirement`.\n\n"
        "**Regra do trabalho:** cada integrante precisa ter pelo menos 1 PR "
        "próprio (aberto, mergeado ou fechado sem merge); quem ainda não tem "
        "aparece com `meetsRequirement: false`. Integrantes sem atividade "
        "aparecem com zeros; pessoas fora do time (bots, colaboradores "
        "externos) são ignoradas. Logins comparados sem diferenciar "
        "maiúsculas.\n\n"
        "Dados de `GET /pulls?state=all` (até 100 PRs, cache de 10 s) e "
        "`GET /contributors` (cache de 60 s) do GitHub, buscados em paralelo."
    ),
    response_description="Integrantes na ordem de TEAM_LOGINS (vazio se não configurado).",
)
async def team(
    github: Annotated[GitHubClient, Depends(get_github_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[TeamMember]:
    if not settings.team_logins:
        # Nada a mostrar: não gasta requisição (nem rate limit) à toa.
        return []
    pulls, contributors = await asyncio.gather(
        github.list_pulls(state="all", limit=PULLS_PER_PAGE),
        github.list_contributors(),
    )
    return build_team(settings.team_logins, pulls, contributors)
