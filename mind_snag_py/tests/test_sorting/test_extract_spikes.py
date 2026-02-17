"""Tests for drift correction in extract_spikes."""

import numpy as np
from mind_snag.sorting.extract_spikes import _apply_drift_correction


def test_drift_correction_identity():
    """Identity weights should not change spike times."""
    spike_times = np.array([1.0, 2.0, 3.0])
    w_nidq = np.array([0.0, 1.0])  # identity
    w_rec = np.array([0.0, 1.0])   # identity
    corrected = _apply_drift_correction(spike_times, w_nidq, w_rec)
    np.testing.assert_allclose(corrected, spike_times, atol=1e-10)


def test_drift_correction_offset():
    """Offset-only correction."""
    spike_times = np.array([1.0, 2.0, 3.0])
    w_nidq = np.array([0.5, 1.0])
    w_rec = np.array([0.0, 1.0])
    corrected = _apply_drift_correction(spike_times, w_nidq, w_rec)
    np.testing.assert_allclose(corrected, spike_times + 0.5, atol=1e-10)


def test_drift_correction_scale():
    """Scale correction."""
    spike_times = np.array([1.0, 2.0, 3.0])
    w_nidq = np.array([0.0, 1.001])
    w_rec = np.array([0.0, 0.999])
    corrected = _apply_drift_correction(spike_times, w_nidq, w_rec)
    expected = 0.999 * (1.001 * spike_times)
    np.testing.assert_allclose(corrected, expected, atol=1e-10)


def test_drift_correction_known_values():
    """Test against known MATLAB reference values."""
    spike_times = np.array([100.0, 200.0, 300.0])
    w_nidq = np.array([0.001, 1.0001])
    w_rec = np.array([-0.002, 0.9999])
    corrected = _apply_drift_correction(spike_times, w_nidq, w_rec)

    # Manual calculation
    st_nidq = 0.001 + 1.0001 * spike_times
    expected = -0.002 + 0.9999 * st_nidq
    np.testing.assert_allclose(corrected, expected, atol=1e-10)
