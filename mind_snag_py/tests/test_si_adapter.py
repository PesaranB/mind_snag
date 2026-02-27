"""Tests for SpikeInterface adapter (Phase 3).

Tests must pass both with and without SpikeInterface installed.
SI-specific tests are skipped when SI is not available.
"""

import numpy as np
import pytest

from mind_snag.types import KilosortOutput, NPcluData

try:
    import spikeinterface as si
    HAS_SI = True
except ImportError:
    HAS_SI = False

requires_si = pytest.mark.skipif(not HAS_SI, reason="SpikeInterface not installed")


class TestGuardedImport:
    def test_module_imports_without_si(self):
        """si_adapter module should import even without SI installed."""
        from mind_snag.io import si_adapter
        assert hasattr(si_adapter, "HAS_SI")

    def test_quality_metrics_imports(self):
        from mind_snag.curation import si_quality_metrics
        assert hasattr(si_quality_metrics, "HAS_SI")


class TestWithoutSI:
    def test_sorting_from_si_raises_without_si(self):
        if HAS_SI:
            pytest.skip("SI is installed, this test is for missing SI")
        from mind_snag.io.si_adapter import sorting_from_si
        with pytest.raises(ImportError, match="SpikeInterface"):
            sorting_from_si(None)

    def test_to_si_sorting_raises_without_si(self):
        if HAS_SI:
            pytest.skip("SI is installed, this test is for missing SI")
        from mind_snag.io.si_adapter import to_si_sorting
        npclu = NPcluData(
            spike_times=np.array([0.1, 0.2]),
            cluster_ids=np.array([1, 1]),
            templates=np.zeros((1, 82, 1)),
            clu_info=np.array([[1, 0]]),
            ks_clu_info=np.array([[1, 0]]),
            pc_feat=None,
            temp_scaling_amps=np.ones(2),
        )
        with pytest.raises(ImportError, match="SpikeInterface"):
            to_si_sorting(npclu)


@requires_si
class TestWithSI:
    def test_sorting_from_si(self):
        """Convert SI sorting to KilosortOutput."""
        from spikeinterface.core import NumpySorting
        from mind_snag.io.si_adapter import sorting_from_si

        times = np.array([0, 100, 200, 300, 400], dtype=np.int64)
        labels = np.array([0, 0, 1, 1, 0], dtype=np.int64)
        sorting = NumpySorting.from_times_labels(
            times_list=times, labels_list=labels,
            sampling_frequency=30000.0,
        )

        ks_out = sorting_from_si(sorting)
        assert isinstance(ks_out, KilosortOutput)
        assert len(ks_out.st) == 5
        assert ks_out.sample_rate == 30000.0

    def test_to_si_sorting(self):
        """Export NPcluData as SI sorting."""
        from mind_snag.io.si_adapter import to_si_sorting

        npclu = NPcluData(
            spike_times=np.array([0.1, 0.2, 0.3, 0.4]),
            cluster_ids=np.array([1, 1, 2, 2]),
            templates=np.zeros((2, 82, 1)),
            clu_info=np.array([[1, 0], [2, 1]]),
            ks_clu_info=np.array([[1, 0]]),
            pc_feat=None,
            temp_scaling_amps=np.ones(4),
        )

        sorting = to_si_sorting(npclu, sample_rate=30000.0)
        assert isinstance(sorting, si.BaseSorting)
        assert len(sorting.get_unit_ids()) == 2
