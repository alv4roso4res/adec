import asyncio
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from api.config import Settings
from api.deps import get_github_client, get_settings
from api.errors import GITHUB_ERROR_RESPONSES, GitHubError
from api.github.client import GitHubClient
from api.schemas.branches import BranchMap
from api.services.branches import build_branch_map

router = APIRouter(prefix="/branches", tags=["branches"])

DEFAULT_BRANCH = "main"
DEFAULT_LIMIT = 15
# Commits da main buscados para achar os commits de cada branch mergeada:
# cobre os merges da janela com folga (uma página do GitHub).
COMMITS_WINDOW = 100
# Cada branch aberta custa um compare; acima disso as demais ficam de fora.
MAX_OPEN_BRANCHES = 10


@router.get(
    "",
    response_model=BranchMap,
    responses=GITHUB_ERROR_RESPONSES,
    operation_id="get_branches",
    summary="Mapa de branches",
    description=(
        "**Card 7 (mapa de branches).** A `main` como linha principal e cada "
        "branch como uma linha que sai dela: as mergeadas voltam para a main no "
        "commit de merge; as abertas ainda não voltaram.\n\n"
        "- **Mergeadas:** saem dos últimos `limit` commits da main (linha de "
        "primeiro pai). Cada merge vira uma branch, com nome e PR lidos da "
        "mensagem do merge, mesmo que a branch já tenha sido apagada.\n"
        "- **Abertas:** branches que existem no GitHub (até "
        f"{MAX_OPEN_BRANCHES}), com os commits de `compare main...branch` e o "
        "PR aberto de cada uma, se houver.\n\n"
        f"Dados de `GET /commits?sha=main` ({COMMITS_WINDOW} commits), "
        "`GET /branches` e `GET /compare` do GitHub (cache de 15 s) e dos PRs "
        "abertos do card 3."
    ),
    response_description="Linha da main e branches, prontas para desenhar.",
)
async def branches(
    github: Annotated[GitHubClient, Depends(get_github_client)],
    settings: Annotated[Settings, Depends(get_settings)],
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=50,
            description=(
                f"Quantos commits da main mostrar, de 1 a 50 (padrão {DEFAULT_LIMIT})."
            ),
            examples=[DEFAULT_LIMIT],
        ),
    ] = DEFAULT_LIMIT,
) -> BranchMap:
    commits, branch_list, pulls = await asyncio.gather(
        github.list_commits(branch=DEFAULT_BRANCH, limit=COMMITS_WINDOW),
        github.list_branches(),
        # Mesma chamada do card 3: sai do cache, sem requisição extra.
        github.list_pulls(state="open", limit=settings.pulls_limit),
    )
    others = [b for b in branch_list if b["name"] != DEFAULT_BRANCH][:MAX_OPEN_BRANCHES]
    comparisons = await asyncio.gather(*(_compare(github, b["name"]) for b in others))

    return build_branch_map(
        commits=commits,
        open_branches=[(b, c) for b, c in zip(others, comparisons) if c is not None],
        pulls=pulls,
        repo_url=f"https://github.com/{settings.github_owner}/{settings.github_repo}",
        default_branch=DEFAULT_BRANCH,
        limit=limit,
    )


async def _compare(github: GitHubClient, name: str) -> dict[str, Any] | None:
    """Compare da main com a branch; None se ela sumiu entre as duas chamadas."""
    try:
        return await github.compare(DEFAULT_BRANCH, name)
    except GitHubError as exc:
        if exc.status_code == 404:
            return None
        raise
