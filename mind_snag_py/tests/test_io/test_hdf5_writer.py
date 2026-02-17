"""Tests for HDF5 writer."""

import h5py
import numpy as np

from mind_snag.io.hdf5_writer import write_hdf5, write_npclu_h5


def test_write_hdf5(tmp_path):
    path = tmp_path / "test.h5"
    data = {
        "x": np.arange(10, dtype=np.float64),
        "y": np.ones((3, 4)),
    }
    write_hdf5(path, data, attrs={"version": 2})

    with h5py.File(path, "r") as f:
        np.testing.assert_array_equal(f["x"][:], np.arange(10))
        assert f["y"].shape == (3, 4)
        assert f.attrs["version"] == 2
        assert "creation_date" in f.attrs


def test_write_npclu_h5(tmp_path):
    path = tmp_path / "test.NPclu.h5"
    n = 50
    write_npclu_h5(
        path,
        spike_times=np.random.rand(n),
        cluster_ids=np.random.randint(0, 5, n).astype(np.int64),
        templates=np.random.randn(5, 82, 10),
        clu_info=np.column_stack([np.arange(5), np.arange(5)]),
        ks_clu_info=np.column_stack([np.arange(3), np.arange(3)]),
        pc_feat=np.random.randn(n, 3, 10),
        temp_scaling_amps=np.random.rand(n),
        ks_version=4,
    )

    with h5py.File(path, "r") as f:
        assert "spike_times" in f
        assert "cluster_ids" in f
        assert "templates" in f
        assert f.attrs["ks_version"] == 4


def test_write_hdf5_skips_none(tmp_path):
    path = tmp_path / "test.h5"
    write_hdf5(path, {"x": np.arange(5), "y": None})

    with h5py.File(path, "r") as f:
        assert "x" in f
        assert "y" not in f
