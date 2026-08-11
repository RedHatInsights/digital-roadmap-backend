from roadmap.services import relevant_cache as cache_module
from roadmap.services.relevant_cache import build_relevant_cache_key
from roadmap.services.relevant_cache import RelevantResponseCache


def test_relevant_response_cache_hit_and_expiry(monkeypatch):
    cache = RelevantResponseCache()
    key = ("relevant-lifecycle-rhel", "1234", False, None, None)
    timeline = iter([0.0, 0.5, 1.2])
    monkeypatch.setattr(cache_module.time, "monotonic", lambda: next(timeline))

    cache.set(key, {"data": [1]}, ttl_seconds=1, maxsize=8)
    assert cache.get(key) == {"data": [1]}
    assert cache.get(key) is None


def test_relevant_response_cache_returns_deep_copy(monkeypatch):
    cache = RelevantResponseCache()
    key = ("relevant-lifecycle-app-streams", "1234", True, None, None)
    monkeypatch.setattr(cache_module.time, "monotonic", lambda: 0.0)
    cache.set(key, {"data": [{"name": "nodejs"}]}, ttl_seconds=10, maxsize=8)

    cached = cache.get(key)
    assert cached is not None
    cached["data"][0]["name"] = "mutated"

    again = cache.get(key)
    assert again is not None
    assert again["data"][0]["name"] == "nodejs"


def test_build_relevant_cache_key_scopes_by_host_groups():
    key_a = build_relevant_cache_key(
        endpoint="relevant-lifecycle-rhel",
        org_id="1234",
        related=False,
        host_groups={"group-a"},
    )
    key_b = build_relevant_cache_key(
        endpoint="relevant-lifecycle-rhel",
        org_id="1234",
        related=False,
        host_groups={"group-b"},
    )
    assert key_a != key_b


def test_build_relevant_cache_key_skips_missing_org():
    key = build_relevant_cache_key(
        endpoint="relevant-lifecycle-rhel",
        org_id="",
        related=False,
        host_groups={"group-a"},
    )
    assert key is None
