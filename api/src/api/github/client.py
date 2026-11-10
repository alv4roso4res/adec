"""Leitura da API do GitHub com cache (TTL + ETag) e tradução de erros.

Os métodos devolvem os dicts/listas crus do GitHub; quem transforma em schema
são os services puros. Escrita (aprovar/mergear) fica para a etapa R9.
"""

from typing import Any
from urllib.parse import urlencode

import httpx

from api.config import Settings
from api.errors import GitHubError
from api.github.cache import ResponseCache

# TTLs fixos por recurso, em segundos. Depois de expirar, a entrada continua no
# cache e o ETag dela vai no If-None-Match: um 304 não gasta rate limit.
TTL_RUNS = 5  # runs e jobs
TTL_PULLS = 10  # PRs, checks e reviews
TTL_COMMITS = 15
TTL_PACKAGES = 30
TTL_CONTRIBUTORS = 60
TTL_USER = 3600  # usuário dono do token

UNREACHABLE_MESSAGE = "Não foi possível falar com o GitHub"


class GitHubClient:
    def __init__(
        self,
        http: httpx.AsyncClient,
        settings: Settings,
        cache: ResponseCache,
    ) -> None:
        self.http = http
        self.settings = settings
        self.cache = cache
        self._repo = f"/repos/{settings.github_owner}/{settings.github_repo}"

    # ------------------------------------------------------------------ base

    async def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        ttl: float,
    ) -> Any:
        params = {k: v for k, v in (params or {}).items() if v is not None}
        key = f"{path}?{urlencode(sorted(params.items()))}" if params else path

        data = self.cache.get_fresh(key)
        if data is not None:
            return data

        async with self.cache.lock(key):
            # Single-flight: quem esperou o lock encontra o cache já preenchido.
            data = self.cache.get_fresh(key)
            if data is not None:
                return data

            entry = self.cache.get_entry(key)
            headers = {}
            if entry is not None and entry.etag:
                headers["If-None-Match"] = entry.etag

            try:
                response = await self.http.get(path, params=params, headers=headers)
            except httpx.TransportError as exc:  # inclui TimeoutException
                raise GitHubError(502, UNREACHABLE_MESSAGE) from exc

            if response.status_code == 304 and entry is not None:
                self.cache.touch(key, ttl)
                return entry.data

            if response.is_success:
                data = response.json()
                self.cache.set(key, data, response.headers.get("ETag"), ttl)
                return data

            raise _to_github_error(response)

    # -------------------------------------------------------------- actions

    async def list_workflow_runs(
        self,
        branch: str | None = None,
        event: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        workflow = self.settings.github_workflow_file
        data = await self._get(
            f"{self._repo}/actions/workflows/{workflow}/runs",
            {
                "branch": branch,
                "event": event,
                "per_page": limit or self.settings.history_limit,
            },
            ttl=TTL_RUNS,
        )
        return data["workflow_runs"]

    async def list_run_jobs(self, run_id: int) -> list[dict[str, Any]]:
        data = await self._get(f"{self._repo}/actions/runs/{run_id}/jobs", ttl=TTL_RUNS)
        return data["jobs"]

    # ---------------------------------------------------------------- pulls

    async def list_pulls(
        self,
        state: str = "open",
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        return await self._get(
            self._pulls_path,
            {"state": state, "per_page": limit or self.settings.pulls_limit},
            ttl=TTL_PULLS,
        )

    async def get_pull(self, number: int) -> dict[str, Any]:
        return await self._get(f"{self._pulls_path}/{number}", ttl=TTL_PULLS)

    async def list_check_runs(self, sha: str) -> list[dict[str, Any]]:
        data = await self._get(
            f"{self._repo}/commits/{sha}/check-runs", ttl=TTL_PULLS
        )
        return data["check_runs"]

    async def list_reviews(self, number: int) -> list[dict[str, Any]]:
        return await self._get(f"{self._pulls_path}/{number}/reviews", ttl=TTL_PULLS)

    def invalidate_pulls(self) -> None:
        """Descarta o cache de PRs (lista, detalhes e reviews) após escrita."""
        self.cache.invalidate(self._pulls_path)

    @property
    def _pulls_path(self) -> str:
        return f"{self._repo}/pulls"

    # ------------------------------------------------------- repo / pessoas

    async def list_commits(
        self,
        branch: str = "main",
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        return await self._get(
            f"{self._repo}/commits",
            {"sha": branch, "per_page": limit or self.settings.history_limit},
            ttl=TTL_COMMITS,
        )

    async def list_contributors(self) -> list[dict[str, Any]]:
        return await self._get(f"{self._repo}/contributors", ttl=TTL_CONTRIBUTORS)

    async def list_package_versions(self, image: str) -> list[dict[str, Any]]:
        owner = self.settings.ghcr_owner
        return await self._get(
            f"/users/{owner}/packages/container/{image}/versions",
            ttl=TTL_PACKAGES,
        )

    async def get_authenticated_user(self) -> dict[str, Any]:
        return await self._get("/user", ttl=TTL_USER)


def _to_github_error(response: httpx.Response) -> GitHubError:
    message = f"Erro {response.status_code} do GitHub"
    try:
        body = response.json()
    except ValueError:
        body = None
    if isinstance(body, dict) and body.get("message"):
        message = body["message"]

    rate_limited = (
        response.status_code in (403, 429)
        and response.headers.get("x-ratelimit-remaining") == "0"
    )
    return GitHubError(response.status_code, message, rate_limited=rate_limited)
