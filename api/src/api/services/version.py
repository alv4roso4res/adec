"""Monta o card 5: versão rodando × `latest` no GHCR × último commit da main.

Função pura: recebe os dicts crus do GitHub (commits da main, runs e versões
de pacote de cada imagem) e a versão em execução; não faz requisição e nunca
altera o que recebe (o cache do GitHubClient devolve o mesmo objeto).
"""

import re
from collections.abc import Mapping, Sequence
from typing import Any

from api.schemas.common import RunStatus
from api.schemas.version import VersionImage, VersionInfo, VersionState
from api.services.commits import latest_run_by_sha
from api.services.pipeline import normalize_status

Raw = Mapping[str, Any]

SHA_TAG_PREFIX = "sha-"
LATEST_TAG = "latest"
# Menor prefixo aceito na comparação (o pipeline usa 7 caracteres).
MIN_SHA_LENGTH = 7
_SHA_RE = re.compile(rf"[0-9a-f]{{{MIN_SHA_LENGTH},40}}")
_FAILED = {RunStatus.FAILURE, RunStatus.CANCELLED}


def same_sha(a: str | None, b: str | None) -> bool:
    """Compara SHAs por prefixo (7 chars do Actions × SHA completo da API).

    Exige pelo menos MIN_SHA_LENGTH caracteres nos dois lados, para um valor
    curto demais não "casar" com qualquer coisa.
    """
    if not a or not b:
        return False
    a, b = a.lower(), b.lower()
    if min(len(a), len(b)) < MIN_SHA_LENGTH:
        return False
    return a.startswith(b) or b.startswith(a)


def published_sha(versions: Sequence[Raw]) -> str | None:
    """SHA da tag `sha-xxxxxxx` que divide a versão de pacote com a `latest`."""
    for version in versions:
        tags = (version.get("metadata") or {}).get("container", {}).get("tags") or []
        if LATEST_TAG in tags:
            sha_tags = [t for t in tags if t.startswith(SHA_TAG_PREFIX)]
            return sha_tags[0][len(SHA_TAG_PREFIX) :] if sha_tags else None
    return None


def build_version(
    running: str,
    main_commits: Sequence[Raw],
    runs: Sequence[Raw],
    package_versions: Mapping[str, Sequence[Raw]],
) -> VersionInfo:
    """`package_versions`: nome da imagem → versões do pacote, na ordem de
    GHCR_IMAGES. `main_commits`: commits da main, o mais novo primeiro."""
    main_sha = main_commits[0]["sha"] if main_commits else None
    images = [
        VersionImage(name=name, published_sha=published_sha(versions))
        for name, versions in package_versions.items()
    ]
    return VersionInfo(
        running=running,
        main_sha=main_sha,
        images=images,
        state=_state(running, main_sha, images, runs),
    )


def _state(
    running: str,
    main_sha: str | None,
    images: list[VersionImage],
    runs: Sequence[Raw],
) -> VersionState:
    if not _SHA_RE.fullmatch(running.lower()):
        return VersionState.DEV

    # `all([])` seria True: sem imagens configuradas nada foi publicado.
    published = bool(images) and all(
        same_sha(image.published_sha, main_sha) for image in images
    )
    if published:
        if same_sha(running, main_sha):
            return VersionState.UP_TO_DATE
        return VersionState.RESTART_PENDING

    # Só o run de push publica imagens; o de pull_request não conta aqui.
    push_runs = [run for run in runs if run.get("event") == "push"]
    run = latest_run_by_sha(push_runs).get(main_sha) if main_sha else None
    if run is not None:
        status = normalize_status(run.get("status"), run.get("conclusion"))
        if status in _FAILED:
            return VersionState.PIPELINE_FAILED
    # Run na fila/rodando, ainda não criado (merge de segundos atrás), ou
    # concluído com o GHCR/cache ainda mostrando a latest anterior — inclusive
    # imagens divergentes no meio da promoção (uma latest já movida, a outra não).
    return VersionState.BUILDING
