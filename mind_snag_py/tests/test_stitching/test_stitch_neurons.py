"""Tests for neuron stitching utilities."""

import numpy as np
from mind_snag.stitching.stitch_neurons import _pairwise_corr


def test_pairwise_corr_identical():
    a = np.array([1.0, 2.0, 3.0, 4.0])
    assert _pairwise_corr(a, a) == pytest.approx(1.0)


def test_pairwise_corr_anticorrelated():
    a = np.array([1.0, 2.0, 3.0, 4.0])
    b = np.array([4.0, 3.0, 2.0, 1.0])
    assert _pairwise_corr(a, b) == pytest.approx(-1.0)


def test_pairwise_corr_with_nans():
    a = np.array([1.0, np.nan, 3.0, 4.0])
    b = np.array([1.0, 2.0, 3.0, 4.0])
    # Should compute correlation on non-NaN pairs
    corr = _pairwise_corr(a, b)
    assert -1.0 <= corr <= 1.0


def test_pairwise_corr_all_nan():
    a = np.array([np.nan, np.nan])
    b = np.array([np.nan, np.nan])
    assert np.isnan(_pairwise_corr(a, b))


def test_pairwise_corr_empty():
    assert np.isnan(_pairwise_corr(np.array([]), np.array([])))


import pytest
