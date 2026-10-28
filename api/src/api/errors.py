from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


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
