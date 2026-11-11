from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api.schemas.common import ErrorResponse


class GitHubError(Exception):
    """Erro devolvido pela API do GitHub, já traduzido para um status nosso.

    `status_code` é o status original do GitHub. `rate_limited` distingue um
    403 de rate limit (503) de um 403 de autenticação/permissão (502), já que
    só o status não basta.
    """

    def __init__(
        self,
        status_code: int,
        message: str,
        *,
        rate_limited: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.rate_limited = rate_limited

    @property
    def http_status(self) -> int:
        if self.rate_limited or self.status_code == 429:
            return 503
        if self.status_code in (401, 403):
            return 502
        # 405 só acontece no merge de PR (PR não mergeável).
        if self.status_code == 405:
            return 409
        if self.status_code >= 500:
            return 502
        return self.status_code


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(GitHubError)
    async def github_error_handler(_: Request, exc: GitHubError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status, content={"detail": exc.message}
        )


# --------------------------------------------------- documentação (OpenAPI)


def _error_doc(description: str, example: str) -> dict[str, Any]:
    return {
        "model": ErrorResponse,
        "description": description,
        "content": {"application/json": {"example": {"detail": example}}},
    }


# Uso: @router.get(..., responses=GITHUB_ERROR_RESPONSES) em toda rota que fala
# com o GitHub. O tests/test_openapi.py exige 502 e 503 nessas rotas.
GITHUB_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    502: _error_doc(
        "Falha ao falar com o GitHub: rede/timeout, token inválido ou sem "
        "permissão, ou erro 5xx do GitHub.",
        "Não foi possível falar com o GitHub",
    ),
    503: _error_doc(
        "Rate limit do GitHub esgotado; tente de novo em alguns minutos.",
        "API rate limit exceeded",
    ),
}

# Para as rotas de escrita (aprovar/mergear PR), na etapa R9.
WRITE_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    403: _error_doc(
        "Ações de escrita desligadas (ENABLE_WRITE_ACTIONS=false).",
        "Ações de escrita estão desligadas",
    ),
    409: _error_doc(
        "Merge recusado pelo GitHub: PR bloqueado, com conflito ou checks "
        "pendentes.",
        "Pull Request is not mergeable",
    ),
    422: _error_doc(
        "Pedido recusado pelo GitHub (ex.: aprovar o próprio PR).",
        "Can not approve your own pull request",
    ),
}
