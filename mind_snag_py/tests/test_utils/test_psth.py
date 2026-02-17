"""Tests for PSTH computation."""

import numpy as np
from mind_snag.utils.psth import psth


def test_psth_empty():
    rate, n_tr = psth([], (-300, 500))
    assert n_tr == 0
    assert len(rate) == 801


def test_psth_single_spike():
    spike_cell = [np.array([0.0])]
    rate, n_tr = psth(spike_cell, (-100, 100), smoothing=10)
    assert n_tr == 1
    assert len(rate) == 201
    # Rate should peak near time 0
    peak_idx = np.argmax(rate)
    assert 90 <= peak_idx <= 110  # near center


def test_psth_multiple_trials():
    rng = np.random.default_rng(42)
    spike_cell = [rng.uniform(-100, 100, 20) for _ in range(50)]
    rate, n_tr = psth(spike_cell, (-200, 200), smoothing=20)
    assert n_tr == 50
    assert len(rate) == 401
    assert np.all(rate >= 0)


def test_psth_smoothing_effect():
    spike_cell = [np.array([0.0]) for _ in range(100)]
    rate_narrow, _ = psth(spike_cell, (-100, 100), smoothing=5)
    rate_wide, _ = psth(spike_cell, (-100, 100), smoothing=30)
    # Narrow smoothing should have higher peak
    assert np.max(rate_narrow) > np.max(rate_wide)
