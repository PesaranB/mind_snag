"""Shared fixtures for mind_snag tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest


@pytest.fixture
def tmp_data_root(tmp_path: Path) -> Path:
    """Create a temporary data root directory structure."""
    data_root = tmp_path / "data"
    data_root.mkdir()
    return data_root


@pytest.fixture
def sample_config(tmp_data_root: Path):
    """Create a sample MindSnagConfig."""
    from mind_snag.config import MindSnagConfig
    return MindSnagConfig(data_root=tmp_data_root)


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_npy_files(tmp_path: Path) -> Path:
    """Create a minimal set of Kilosort output NPY files."""
    ks_dir = tmp_path / "ks_output"
    ks_dir.mkdir()

    n_spikes = 100
    n_templates = 5
    n_channels = 10
    n_time = 82
    sample_rate = 30000.0

    # params.py
    (ks_dir / "params.py").write_text(
        f"sample_rate = {sample_rate}\n"
        f"n_channels_dat = {n_channels}\n"
        "dtype = 'int16'\n"
        "hp_filtered = True\n"
    )

    # spike_times.npy
    st = np.sort(np.random.randint(0, 1000000, n_spikes)).astype(np.int64)
    np.save(ks_dir / "spike_times.npy", st)

    # spike_templates.npy
    spike_templates = np.random.randint(0, n_templates, n_spikes).astype(np.int64)
    np.save(ks_dir / "spike_templates.npy", spike_templates)

    # spike_clusters.npy
    np.save(ks_dir / "spike_clusters.npy", spike_templates.copy())

    # amplitudes.npy
    np.save(ks_dir / "amplitudes.npy", np.random.rand(n_spikes).astype(np.float64))

    # templates.npy
    templates = np.random.randn(n_templates, n_time, n_channels).astype(np.float64)
    np.save(ks_dir / "templates.npy", templates)

    # channel_positions.npy
    coords = np.column_stack([
        np.zeros(n_channels),
        np.arange(n_channels) * 20.0,
    ])
    np.save(ks_dir / "channel_positions.npy", coords)

    # channel_map.npy
    np.save(ks_dir / "channel_map.npy", np.arange(n_channels, dtype=np.int64))

    # whitening_mat_inv.npy
    np.save(ks_dir / "whitening_mat_inv.npy", np.eye(n_channels))

    # pc_features.npy
    pc_feat = np.random.randn(n_spikes, 3, n_channels).astype(np.float64)
    np.save(ks_dir / "pc_features.npy", pc_feat)

    # pc_feature_ind.npy
    pc_feat_ind = np.tile(np.arange(n_channels), (n_templates, 1)).astype(np.int64)
    np.save(ks_dir / "pc_feature_ind.npy", pc_feat_ind)

    # cluster_group.tsv
    with open(ks_dir / "cluster_group.tsv", "w") as f:
        f.write("cluster_id\tgroup\n")
        for i in range(n_templates):
            label = "good" if i < 3 else "mua"
            f.write(f"{i}\t{label}\n")

    # cluster_KSLabel.tsv (same content for KS4)
    with open(ks_dir / "cluster_KSLabel.tsv", "w") as f:
        f.write("cluster_id\tKSLabel\n")
        for i in range(n_templates):
            label = "good" if i < 3 else "mua"
            f.write(f"{i}\t{label}\n")

    return ks_dir
