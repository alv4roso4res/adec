from api.github.cache import ResponseCache


class FakeClock:
    def __init__(self, now: float = 1000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def make_cache() -> tuple[ResponseCache, FakeClock]:
    clock = FakeClock()
    return ResponseCache(clock=clock), clock


def test_get_fresh_within_ttl_and_none_after_expiry():
    cache, clock = make_cache()
    cache.set("pulls", [{"number": 1}], '"etag-1"', ttl=10)

    clock.advance(9.9)
    assert cache.get_fresh("pulls") == [{"number": 1}]

    clock.advance(0.1)
    assert cache.get_fresh("pulls") is None


def test_get_entry_keeps_data_and_etag_after_expiry():
    cache, clock = make_cache()
    cache.set("pulls", {"a": 1}, '"etag-1"', ttl=10)

    clock.advance(60)
    entry = cache.get_entry("pulls")

    assert entry is not None
    assert entry.data == {"a": 1}
    assert entry.etag == '"etag-1"'


def test_touch_renews_ttl_without_changing_data_or_etag():
    cache, clock = make_cache()
    cache.set("pulls", {"a": 1}, '"etag-1"', ttl=10)
    clock.advance(15)
    assert cache.get_fresh("pulls") is None

    cache.touch("pulls", ttl=10)

    assert cache.get_fresh("pulls") == {"a": 1}
    assert cache.get_entry("pulls").etag == '"etag-1"'
    clock.advance(10)
    assert cache.get_fresh("pulls") is None


def test_touch_missing_key_does_nothing():
    cache, _ = make_cache()

    cache.touch("nada", ttl=10)

    assert cache.get_entry("nada") is None


def test_set_overwrites_data_and_etag():
    cache, _ = make_cache()
    cache.set("pulls", {"v": 1}, '"etag-1"', ttl=10)

    cache.set("pulls", {"v": 2}, None, ttl=10)

    entry = cache.get_entry("pulls")
    assert entry.data == {"v": 2}
    assert entry.etag is None


def test_invalidate_removes_only_keys_with_prefix():
    cache, _ = make_cache()
    for key in ("pulls:open", "pulls:42", "runs:latest", "xpulls"):
        cache.set(key, key, None, ttl=10)

    cache.invalidate("pulls")

    assert cache.get_entry("pulls:open") is None
    assert cache.get_entry("pulls:42") is None
    assert cache.get_fresh("runs:latest") == "runs:latest"
    assert cache.get_fresh("xpulls") == "xpulls"


def test_missing_key_returns_none():
    cache, _ = make_cache()

    assert cache.get_fresh("nada") is None
    assert cache.get_entry("nada") is None


def test_lock_is_per_key():
    cache, _ = make_cache()

    assert cache.lock("a") is cache.lock("a")
    assert cache.lock("a") is not cache.lock("b")
