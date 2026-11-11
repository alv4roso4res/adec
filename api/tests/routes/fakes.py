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
        packages: dict[str, list[dict[str, Any]]] | None = None,
        pulls: list[dict[str, Any]] | None = None,
        contributors: list[dict[str, Any]] | None = None,
        error: GitHubError | None = None,
        package_errors: dict[str, GitHubError] | None = None,
    ) -> None:
        self.runs = runs or []
        self.jobs = jobs or []
        self.commits = commits or []
        self.packages = packages or {}
        self.pulls = pulls or []
        self.contributors = contributors or []
        self.error = error
        # Erro só na leitura de uma imagem (ex.: 404 de pacote não publicado).
        self.package_errors = package_errors or {}
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

    async def list_package_versions(self, image: str) -> list[dict[str, Any]]:
        self._record("list_package_versions", {"image": image})
        if image in self.package_errors:
            raise self.package_errors[image]
        return self.packages.get(image, [])

    async def list_pulls(self, **kwargs: Any) -> list[dict[str, Any]]:
        self._record("list_pulls", kwargs)
        return self.pulls

    async def list_contributors(self) -> list[dict[str, Any]]:
        self._record("list_contributors", {})
        return self.contributors
