"""Tests for stitching backend dispatch (Phase 4)."""

import pytest

from mind_snag.stitching.backends import get_backend, NativeBackend, UnitMatchBackend


class TestGetBackend:
    def test_native(self):
        backend = get_backend("native")
        assert isinstance(backend, NativeBackend)

    def test_unitmatch(self):
        backend = get_backend("unitmatch")
        assert isinstance(backend, UnitMatchBackend)

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown stitching backend"):
            get_backend("invalid_backend")

    def test_backend_has_run_method(self):
        for name in ("native", "unitmatch"):
            backend = get_backend(name)
            assert hasattr(backend, "run")
            assert callable(backend.run)


class TestNativeBackend:
    def test_instantiation(self):
        backend = NativeBackend()
        assert hasattr(backend, "run")


class TestUnitMatchBackend:
    def test_instantiation(self):
        backend = UnitMatchBackend()
        assert hasattr(backend, "run")
