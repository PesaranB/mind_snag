"""Tests for Kilosort directory loader."""

import numpy as np

from mind_snag.io.ks_loader import load_ks_dir


def test_load_ks_dir(sample_npy_files):
    sp = load_ks_dir(sample_npy_files, exclude_noise=False)

    assert sp.sample_rate == 30000.0
    assert len(sp.st) == 100
    assert len(sp.spike_templates) == 100
    assert len(sp.clu) == 100
    assert len(sp.temp_scaling_amps) == 100
    assert sp.temps.shape == (5, 82, 10)
    assert len(sp.chan_map) == 10
    assert sp.pc_feat.shape == (100, 3, 10)


def test_load_ks_dir_exclude_noise(sample_npy_files):
    # Modify cluster_group.tsv to mark cluster 0 as noise
    with open(sample_npy_files / "cluster_group.tsv", "w") as f:
        f.write("cluster_id\tgroup\n")
        f.write("0\tnoise\n")
        f.write("1\tgood\n")
        f.write("2\tgood\n")
        f.write("3\tmua\n")
        f.write("4\tmua\n")

    sp = load_ks_dir(sample_npy_files, exclude_noise=True)

    # Cluster 0 spikes should be excluded
    assert 0 not in sp.cids
    assert 0 not in sp.clu


def test_load_ks_dir_no_pcs(sample_npy_files):
    sp = load_ks_dir(sample_npy_files, load_pcs=False)
    assert sp.pc_feat is None
    assert sp.pc_feat_ind is None
