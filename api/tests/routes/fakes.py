"""Fake do GitHubClient para os testes de rota (sem rede)."""

from typing import Any

from api.errors import GitHubError

RATE_LIMIT = GitHubError(403, "API rate limit exceeded", rate_limited=True)


class FakeGitHubClient:
    """Substitui o GitHubClient: devolve dados prontos e registra as chamadas."""

    def __init__(
        self,
        runs: list[dict[str, Any]] | None = None,
        jobs: list[dict[str, Any]] | None = None,
        commits: list[dict[str, Any]] | None = None,
        error: GitHubError | None = None,
    ) -> None:
        self.runs = runs or []
        self.jobs = jobs or []
        self.commits = commits or []
        self.error = error
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def _record(self, name: str, kwargs: dict[str, Any]) -> None:
        self.calls.append((name, kwargs))
        if self.error:
            raise self.error

    async def list_workflow_runs(self, **kwargs: Any) -> list[dict[str, Any]]:
        self._record("list_workflow_runs", kwargs)
        return self.runs[: kwargs.get("limit") or None]

    async def list_run_jobs(self, run_id: int) -> list[dict[str, Any]]:
        self._record("list_run_jobs", {"run_id": run_id})
        return self.jobs

    async def list_commits(self, **kwargs: Any) -> list[dict[str, Any]]:
        self._record("list_commits", kwargs)
        return self.commits[: kwargs.get("limit") or None]
