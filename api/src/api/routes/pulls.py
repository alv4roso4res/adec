import asyncio
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path

from api.config import Settings
from api.deps import get_github_client, get_settings, require_write_actions
from api.errors import GITHUB_ERROR_RESPONSES, WRITE_ERROR_RESPONSES
from api.github.client import GitHubClient
from api.schemas.pulls import PullItem, WriteResult
from api.services.pulls import build_pulls

router = APIRouter(prefix="/pulls", tags=["pulls"])

WRITE_RESPONSES = {**GITHUB_ERROR_RESPONSES, **WRITE_ERROR_RESPONSES}

PullNumber = Annotated[
    int,
    Path(ge=1, description="Número do PR no repositório monitorado.", examples=[7]),
]


async def fetch_token_login(github: GitHubClient, settings: Settings) -> str | None:
    """Login do dono do token, só quando a escrita está ligada.

    Sem token, `/user` daria 401; com a escrita desligada ninguém aprova, então
    a chamada seria desperdício. Nos dois casos, None (e `canApprove` false).
    """
    if not (settings.github_token and settings.enable_write_actions):
        return None
    user = await github.get_authenticated_user()
    return user.get("login")


async def _fetch_pull_data(
    github: GitHubClient, pull: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    number = pull["number"]
    return await asyncio.gather(
        github.get_pull(number),
        github.list_check_runs(pull["head"]["sha"]),
        github.list_reviews(number),
    )


@router.get(
    "",
    response_model=list[PullItem],
    responses=GITHUB_ERROR_RESPONSES,
    operation_id="get_pulls",
    summary="PRs abertos com badges",
    description=(
        "**Card 3 (PRs abertos).** Até `PULLS_LIMIT` PRs abertos, do mais novo "
        "para o mais antigo, com checks, aprovações, badge e o que o painel "
        "pode fazer com cada um.\n\n"
        "**Badges** (vale o primeiro que se aplica):\n\n"
        "| Badge | Quando |\n"
        "|---|---|\n"
        "| `draft` | PR em rascunho |\n"
        "| `conflict` | conflito com a base (`mergeable_state` dirty) |\n"
        "| `checks_failed` | algum check falhou, foi cancelado ou deu timeout |\n"
        "| `waiting_checks` | algum check na fila/rodando, ou nenhum check contado |\n"
        "| `computing` | o GitHub ainda calcula se dá para mergear (unknown/null) |\n"
        "| `needs_approval` | checks verdes, mas a proteção bloqueia (blocked) |\n"
        "| `ready` | pronto para mergear (clean, unstable ou has_hooks) |\n\n"
        "Checks: vale a execução mais recente de cada um; `skipped`/`neutral` "
        "não contam. `approvals` conta os revisores cujo último review "
        "(ignorando comentários) é APPROVED.\n\n"
        "**`canApprove`**: escrita ligada (`ENABLE_WRITE_ACTIONS`), PR de "
        "outra pessoa que não o dono do token, fora de rascunho e ainda não "
        "aprovado por ele. **`canMerge`** = escrita ligada, **mesmo com o PR "
        "bloqueado, de propósito**: na demo, o botão tenta e o GitHub recusa "
        "o merge (a proteção da `main` é quem manda).\n\n"
        "Dados de `GET /pulls?state=open` e, para cada PR, em paralelo, "
        "`GET /pulls/{n}`, `GET /commits/{sha}/check-runs` e "
        "`GET /pulls/{n}/reviews` (cache de 10 s). `GET /user` só é chamado "
        "com token e escrita ligada."
    ),
    response_description="PRs abertos (vazio se não houver nenhum).",
)
async def pulls(
    github: Annotated[GitHubClient, Depends(get_github_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[PullItem]:
    pulls = await github.list_pulls(state="open", limit=settings.pulls_limit)
    if not pulls:
        return []

    per_pull, token_login = await asyncio.gather(
        asyncio.gather(*(_fetch_pull_data(github, pull) for pull in pulls)),
        fetch_token_login(github, settings),
    )
    details, check_runs, reviews = {}, {}, {}
    for pull, (detail, checks, pull_reviews) in zip(pulls, per_pull, strict=True):
        number = pull["number"]
        details[number] = detail
        check_runs[number] = checks
        reviews[number] = pull_reviews

    return build_pulls(
        pulls,
        details,
        check_runs,
        reviews,
        token_login=token_login,
        write_enabled=settings.enable_write_actions,
    )


@router.post(
    "/{number}/approve",
    response_model=WriteResult,
    responses=WRITE_RESPONSES,
    dependencies=[Depends(require_write_actions)],
    operation_id="approve_pull",
    summary="Aprovar PR",
    description=(
        "**Card 3, botão Aprovar.** Envia um review `APPROVE` no PR em nome do "
        "dono do token do backend (`POST /pulls/{n}/reviews`), sem cache. "
        "Depois do sucesso, o cache de PRs é descartado e o próximo "
        "`GET /api/pulls` já mostra a aprovação.\n\n"
        "Exige `ENABLE_WRITE_ACTIONS=true` (senão 403, sem falar com o "
        "GitHub). Recusas do GitHub chegam com a mensagem original em "
        "`detail`: aprovar o próprio PR → 422."
    ),
    response_description="PR aprovado.",
)
async def approve_pull(
    number: PullNumber,
    github: Annotated[GitHubClient, Depends(get_github_client)],
) -> WriteResult:
    await github.approve_pull(number)
    return WriteResult(ok=True, message=f"PR #{number} aprovado")


@router.post(
    "/{number}/merge",
    response_model=WriteResult,
    responses=WRITE_RESPONSES,
    dependencies=[Depends(require_write_actions)],
    operation_id="merge_pull",
    summary="Mergear PR",
    description=(
        "**Card 3, botão Merge.** Mergeia o PR com `MERGE_METHOD` (`PUT "
        "/pulls/{n}/merge`), sem cache; depois do sucesso, o cache de PRs é "
        "descartado. A mensagem traz o SHA curto do commit de merge.\n\n"
        "**A recusa é esperada:** o botão fica habilitado mesmo com o PR "
        "bloqueado. Se faltar aprovação, o check `build-test` estiver vermelho "
        "ou pendente, ou houver conflito, o GitHub recusa (405 → **409**, "
        "com a mensagem original em `detail`). É a prova ao vivo de que a "
        "`main` está protegida: nem o dono do token passa por cima.\n\n"
        "Exige `ENABLE_WRITE_ACTIONS=true` (senão 403, sem falar com o "
        "GitHub). 409 do GitHub (ex.: a branch do PR mudou) → 409; 422 → 422."
    ),
    response_description="PR mergeado.",
)
async def merge_pull(
    number: PullNumber,
    github: Annotated[GitHubClient, Depends(get_github_client)],
) -> WriteResult:
    data = await github.merge_pull(number)
    short_sha = (data or {}).get("sha", "")[:7]
    message = f"PR #{number} mergeado ({short_sha})" if short_sha else f"PR #{number} mergeado"
    return WriteResult(ok=True, message=message)
