"""Tests for UnitMatch adapter (Phase 4).

Tests pass both with and without UnitMatchPy installed.
"""

import numpy as np
import pytest

try:
    import UnitMatchPy
    HAS_UM = True
except ImportError:
    HAS_UM = False


class TestGuardedImport:
    def test_module_imports(self):
        """unitmatch_adapter imports even without UnitMatchPy."""
        from mind_snag.stitching import unitmatch_adapter
        assert hasattr(unitmatch_adapter, "HAS_UM")

    def test_backends_module_imports(self):
        from mind_snag.stitching import backends
        assert "unitmatch" in backends._BACKENDS


class TestWfCorr:
    def test_identical_waveforms(self):
        from mind_snag.stitching.unitmatch_adapter import _wf_corr
        wf = np.random.randn(61)
        assert _wf_corr(wf, wf) == pytest.approx(1.0)

    def test_anticorrelated(self):
        from mind_snag.stitching.unitmatch_adapter import _wf_corr
        wf = np.random.randn(61)
        assert _wf_corr(wf, -wf) == pytest.approx(-1.0)

    def test_nan_waveform(self):
        from mind_snag.stitching.unitmatch_adapter import _wf_corr
        wf = np.random.randn(61)
        nan_wf = np.full(61, np.nan)
        assert np.isnan(_wf_corr(wf, nan_wf))

    def test_empty_waveform(self):
        from mind_snag.stitching.unitmatch_adapter import _wf_corr
        assert np.isnan(_wf_corr(np.array([]), np.array([])))


class TestRunUnitmatchWithoutLib:
    def test_raises_without_unitmatchpy(self):
        if HAS_UM:
            pytest.skip("UnitMatchPy is installed")
        from mind_snag.config import MindSnagConfig
        from mind_snag.stitching.unitmatch_adapter import run_unitmatch

        cfg = MindSnagConfig()
        with pytest.raises(ImportError, match="UnitMatchPy"):
            run_unitmatch(cfg, "250224", ["007", "009"], "LPPC", 1, True)


class TestConfigBackend:
    def test_default_backend_is_native(self):
        from mind_snag.config import MindSnagConfig
        cfg = MindSnagConfig()
        assert cfg.stitching.backend == "native"

    def test_set_unitmatch_backend(self):
        from mind_snag.config import MindSnagConfig
        cfg = MindSnagConfig()
        cfg.stitching.backend = "unitmatch"
        assert cfg.stitching.backend == "unitmatch"

    def test_top_k_default(self):
        from mind_snag.config import MindSnagConfig
        cfg = MindSnagConfig()
        assert cfg.stitching.top_k == 3
