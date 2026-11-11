import asyncio
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from api.config import Settings
from api.deps import get_github_client, get_settings
from api.errors import GITHUB_ERROR_RESPONSES, GitHubError
from api.github.client import GitHubClient
from api.routes.commits import fetch_main_commits
from api.routes.pipeline import fetch_history_runs
from api.schemas.version import VersionInfo
from api.services.version import build_version

router = APIRouter(prefix="/version", tags=["version"])


async def _package_versions(github: GitHubClient, image: str) -> list[dict[str, Any]]:
    # 404 = pacote ainda não publicado (antes do primeiro deploy): o card mostra
    # a imagem sem versão em vez de quebrar. Os demais erros sobem.
    try:
        return await github.list_package_versions(image)
    except GitHubError as exc:
        if exc.status_code == 404:
            return []
        raise


@router.get(
    "",
    response_model=VersionInfo,
    responses=GITHUB_ERROR_RESPONSES,
    operation_id="get_version",
    summary="Versão rodando × publicada × main",
    description=(
        "**Card 5 (versão publicada vs. main).** Compara a versão em execução "
        "(APP_VERSION), a tag `latest` de cada imagem no GHCR (GHCR_IMAGES) e o "
        "último commit da `main`, e resume em `state`: `up_to_date`, "
        "`restart_pending`, `building`, `pipeline_failed` ou `dev`. SHAs são "
        "comparados por prefixo.\n\n"
        "Dados de `GET /users/{owner}/packages/container/{imagem}/versions` "
        "(cache de 30 s; exige token com `read:packages`, mesmo com pacote "
        "público). Commits da main e runs vêm das mesmas chamadas dos cards 6 e "
        "2, já em cache, sem requisição extra. Imagem ainda não publicada (404) "
        "aparece com `publishedSha: null`."
    ),
    response_description="Versões e a situação da produção em relação à main.",
)
async def version(
    github: Annotated[GitHubClient, Depends(get_github_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> VersionInfo:
    commits, runs, *packages = await asyncio.gather(
        fetch_main_commits(github),
        fetch_history_runs(github, settings),
        *(_package_versions(github, image) for image in settings.ghcr_images),
    )
    return build_version(
        running=settings.app_version,
        main_commits=commits,
        runs=runs,
        package_versions=dict(zip(settings.ghcr_images, packages, strict=True)),
    )
