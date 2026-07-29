"""Tests for notificator.cache — inter-org cache management."""

from __future__ import annotations

import pytest

from notificator.cache import clear_caches
from roadmap.v1.lifecycle.app_streams import app_stream_from_package
from roadmap.v1.lifecycle.app_streams import NEVRA


SAMPLE_NEVRAS = [
    "glibc-0:2.34-168.el9_6.14.x86_64",
    "bash-0:5.1.8-9.el9.x86_64",
    "python3-libs-0:3.9.21-1.el9.x86_64",
]


@pytest.fixture(autouse=True)
def _isolate_caches():
    """Ensure each test starts and ends with clean caches."""
    NEVRA.from_string.cache_clear()
    app_stream_from_package.cache_clear()
    yield
    NEVRA.from_string.cache_clear()
    app_stream_from_package.cache_clear()


class TestClearCaches:
    """clear_caches(): both caches are emptied and their prior sizes are logged."""

    def test_clears_nevra_cache(self):
        """Populated NEVRA cache is emptied after clear_caches()."""
        for nevra in SAMPLE_NEVRAS:
            NEVRA.from_string(nevra)

        assert NEVRA.from_string.cache_info().currsize == len(SAMPLE_NEVRAS)

        clear_caches()

        assert NEVRA.from_string.cache_info().currsize == 0

    def test_clears_app_stream_from_package_cache(self):
        """Populated app_stream_from_package cache is emptied after clear_caches()."""
        for nevra in SAMPLE_NEVRAS:
            app_stream_from_package(nevra, 9)

        assert app_stream_from_package.cache_info().currsize == len(SAMPLE_NEVRAS)

        clear_caches()

        assert app_stream_from_package.cache_info().currsize == 0

    def test_clears_both_caches_simultaneously(self):
        """A single clear_caches() call empties both caches, not just one."""
        NEVRA.from_string(SAMPLE_NEVRAS[0])
        app_stream_from_package(SAMPLE_NEVRAS[0], 9)

        assert NEVRA.from_string.cache_info().currsize == 1
        assert app_stream_from_package.cache_info().currsize == 1

        clear_caches()

        assert NEVRA.from_string.cache_info().currsize == 0
        assert app_stream_from_package.cache_info().currsize == 0

    def test_noop_on_empty_caches(self):
        """Calling clear_caches() on already-empty caches does not raise."""
        assert NEVRA.from_string.cache_info().currsize == 0
        assert app_stream_from_package.cache_info().currsize == 0

        clear_caches()

        assert NEVRA.from_string.cache_info().currsize == 0
        assert app_stream_from_package.cache_info().currsize == 0

    def test_caches_repopulate_after_clear(self):
        """After clearing, new calls populate fresh cache entries (cache still works)."""
        nevra_str = SAMPLE_NEVRAS[0]
        NEVRA.from_string(nevra_str)
        clear_caches()

        assert NEVRA.from_string.cache_info().currsize == 0

        result_a = NEVRA.from_string(nevra_str)
        result_b = NEVRA.from_string(nevra_str)

        assert NEVRA.from_string.cache_info().currsize == 1
        assert NEVRA.from_string.cache_info().hits >= 1
        assert result_a is result_b

    def test_logs_cache_sizes_before_clear(self, mocker):
        """The debug log message reports the cache sizes that existed *before* clearing."""
        log_debug = mocker.patch("notificator.cache.logger.debug")

        for nevra in SAMPLE_NEVRAS:
            NEVRA.from_string(nevra)
        app_stream_from_package(SAMPLE_NEVRAS[0], 8)
        app_stream_from_package(SAMPLE_NEVRAS[0], 9)

        clear_caches()

        log_debug.assert_called_once_with(
            "Cleared inter-org caches",
            nevra_cache_size=len(SAMPLE_NEVRAS),
            app_stream_cache_size=2,
        )

    def test_multiple_clears_in_sequence(self):
        """Simulates the notificator loop: populate → clear → populate → clear."""
        org1_nevras = SAMPLE_NEVRAS[:2]
        org2_nevras = SAMPLE_NEVRAS[1:]

        for nevra in org1_nevras:
            NEVRA.from_string(nevra)
            app_stream_from_package(nevra, 9)
        assert NEVRA.from_string.cache_info().currsize == 2
        assert app_stream_from_package.cache_info().currsize == 2

        clear_caches()
        assert NEVRA.from_string.cache_info().currsize == 0

        for nevra in org2_nevras:
            NEVRA.from_string(nevra)
            app_stream_from_package(nevra, 9)
        assert NEVRA.from_string.cache_info().currsize == 2
        assert app_stream_from_package.cache_info().currsize == 2

        clear_caches()
        assert NEVRA.from_string.cache_info().currsize == 0
        assert app_stream_from_package.cache_info().currsize == 0

    def test_nevra_identity_lost_after_clear(self):
        """After clearing, the same NEVRA string produces an equal but distinct object."""
        nevra_str = SAMPLE_NEVRAS[0]
        before = NEVRA.from_string(nevra_str)

        clear_caches()

        after = NEVRA.from_string(nevra_str)
        assert before == after
        assert before is not after
