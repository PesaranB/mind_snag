"""Tests for sorting utilities."""

import numpy as np
from mind_snag.utils.sorting_utils import sort_spikes_by_rt, get_rasters


def test_sort_spikes_by_rt():
    rt = np.array([300.0, 100.0, 200.0])
    spikes = [np.array([10, 20]), np.array([30]), np.array([40, 50, 60])]
    sorted_rt, sorted_spx = sort_spikes_by_rt(rt, spikes)
    np.testing.assert_array_equal(sorted_rt, [100.0, 200.0, 300.0])
    np.testing.assert_array_equal(sorted_spx[0], [30])
    np.testing.assert_array_equal(sorted_spx[1], [40, 50, 60])
    np.testing.assert_array_equal(sorted_spx[2], [10, 20])


def test_sort_empty_rt():
    sorted_rt, sorted_spx = sort_spikes_by_rt(np.array([]), [])
    assert len(sorted_rt) == 0


def test_get_rasters():
    spike_cell = [np.array([10, 20]), np.array([15])]
    x, y = get_rasters(spike_cell, (-300, 500))
    assert len(x) == 3
    assert len(y) == 3


def test_get_rasters_empty():
    x, y = get_rasters([], (-300, 500))
    assert len(x) == 0
    assert len(y) == 0
