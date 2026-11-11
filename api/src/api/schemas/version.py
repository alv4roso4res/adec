"""Resposta do card 5 (versão rodando × publicada no GHCR × main).

Os exemplos vêm das fixtures reais em tests/fixtures/github/
(package_versions_*.json e commits.json).
"""

from enum import StrEnum

from pydantic import ConfigDict, Field

from api.schemas.common import ApiModel

_MAIN_SHA = "e8eb3e0aa85bb8e7c0af9c52ae69197d024e941c"
_IMAGES_EXAMPLE = [
    {"name": "adec-api", "publishedSha": "e8eb3e0"},
    {"name": "adec-frontend", "publishedSha": "e8eb3e0"},
]


class VersionState(StrEnum):
    """Situação da produção em relação à main (avaliada nesta ordem):

    - `dev`: a API não está rodando de uma imagem do pipeline (APP_VERSION não
      é um SHA, ex.: "dev");
    - `up_to_date`: a `latest` de todas as imagens e a versão rodando são o
      último commit da main;
    - `restart_pending`: a `latest` de todas as imagens já é a main, mas a
      produção ainda roda a versão anterior (o vigia ainda não trocou o
      container);
    - `pipeline_failed`: a `latest` não é a main e o run de push da main falhou
      ou foi cancelado (a produção fica na versão anterior);
    - `building`: a `latest` não é a main (ou as imagens divergem entre si) e o
      run de push da main está na fila, rodando, ainda não apareceu ou acabou
      de terminar (publicação/cache se atualizando).
    """

    UP_TO_DATE = "up_to_date"
    RESTART_PENDING = "restart_pending"
    BUILDING = "building"
    PIPELINE_FAILED = "pipeline_failed"
    DEV = "dev"


class VersionImage(ApiModel):
    """Uma imagem no GHCR e o commit para o qual a tag `latest` aponta."""

    name: str = Field(
        description="Nome da imagem no GHCR (GHCR_IMAGES).",
        examples=["adec-api", "adec-frontend"],
    )
    published_sha: str | None = Field(
        description=(
            "SHA curto da tag `sha-xxxxxxx` que está na mesma versão de pacote "
            "que a `latest`; null se não há `latest` (ou ela não tem tag sha-)."
        ),
        examples=["e8eb3e0"],
    )


class VersionInfo(ApiModel):
    """Card 5: versão rodando × versão publicada no GHCR × último commit da main.

    SHAs são comparados por prefixo: o pipeline usa 7 caracteres e
    `git rev-parse --short` pode usar mais.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "running": "e8eb3e0",
                    "mainSha": _MAIN_SHA,
                    "images": _IMAGES_EXAMPLE,
                    "state": "up_to_date",
                }
            ]
        }
    )

    running: str = Field(
        description='Versão em execução (APP_VERSION): SHA curto da imagem ou "dev".',
        examples=["e8eb3e0", "dev"],
    )
    main_sha: str | None = Field(
        description="SHA completo do último commit da main; null se a main está vazia.",
        examples=[_MAIN_SHA],
    )
    images: list[VersionImage] = Field(
        description="Uma entrada por imagem de GHCR_IMAGES, na mesma ordem.",
        examples=[_IMAGES_EXAMPLE],
    )
    state: VersionState = Field(
        description="Situação da produção (ver o schema VersionState).",
        examples=["up_to_date", "building"],
    )
