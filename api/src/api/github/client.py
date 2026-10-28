import httpx


class GitHubClient:
    def __init__(self, http: httpx.AsyncClient, owner: str, repo: str) -> None:
        self.http = http
        self.owner = owner
        self.repo = repo
