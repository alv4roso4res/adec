"""Cache em memória das respostas do GitHub, com TTL e ETag.

Diferente do cachetools.TTLCache, a entrada expirada NÃO é descartada: o
GitHubClient usa o ETag dela para mandar If-None-Match e, se vier 304, só
renova a validade com `touch` (requisição condicional não gasta rate limit).
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class CacheEntry:
    data: Any
    etag: str | None
    expires_at: float


class ResponseCache:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._entries: dict[str, CacheEntry] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def get_fresh(self, key: str) -> Any | None:
        """Dados da entrada, se ela existe e ainda está dentro do TTL."""
        entry = self._entries.get(key)
        if entry is None or self._clock() >= entry.expires_at:
            return None
        return entry.data

    def get_entry(self, key: str) -> CacheEntry | None:
        """A entrada mesmo expirada (para reaproveitar o ETag)."""
        return self._entries.get(key)

    def set(self, key: str, data: Any, etag: str | None, ttl: float) -> None:
        self._entries[key] = CacheEntry(data, etag, self._clock() + ttl)

    def touch(self, key: str, ttl: float) -> None:
        """Renova a validade mantendo dados e ETag (resposta 304)."""
        entry = self._entries.get(key)
        if entry is not None:
            entry.expires_at = self._clock() + ttl

    def invalidate(self, prefix: str) -> None:
        """Remove todas as chaves que começam com `prefix`."""
        for key in [k for k in self._entries if k.startswith(prefix)]:
            del self._entries[key]

    def lock(self, key: str) -> asyncio.Lock:
        """Um Lock por chave, para evitar requisições iguais simultâneas."""
        return self._locks.setdefault(key, asyncio.Lock())
