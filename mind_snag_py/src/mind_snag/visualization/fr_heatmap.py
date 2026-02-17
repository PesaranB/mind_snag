"""Depth-sorted firing rate heatmap visualization.

Ports fr_heatmap.m. For each recording, loads cluster RasterData,
computes PSTHs, sorts by probe depth, and renders a heatmap.
"""

from __future__ import annotations

import logging
from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import gaussian_filter

from mind_snag.config import MindSnagConfig
from mind_snag.io.cluster_groups import read_cluster_groups
from mind_snag.io.mat_reader import load_mat
from mind_snag.utils.channel_info import get_np_chan_depth_info
from mind_snag.utils.psth import psth
from mind_snag.utils.sorting_utils import sort_spikes_by_rt
from mind_snag.utils.paths import (
    ks_output_dir, rec_name_str, group_flag_str, raster_data_filename,
)

logger = logging.getLogger(__name__)


def fr_heatmap(
    cfg: MindSnagConfig,
    day: str,
    tower: str,
    np_num: int,
    grouped: bool,
    recs: list[str] | None = None,
    show: bool = True,
    save_path: Path | None = None,
) -> plt.Figure:
    """Generate depth-sorted firing rate heatmaps.

    Parameters
    ----------
    cfg : pipeline configuration
    day : recording date (YYMMDD)
    tower : recording setup name
    np_num : probe number
    grouped : whether recordings are concatenated
    recs : optional list of recording numbers (auto-detected if None)
    show : whether to call plt.show()
    save_path : optional path to save figure

    Returns
    -------
    matplotlib Figure
    """
    cfg.validate()
    data_root = cfg.data_root

    if recs is None:
        recs = _get_valid_recs(data_root, day)

    n_r = len(recs)
    fig, axes = plt.subplots(1, n_r, figsize=(6 * n_r, 8), squeeze=False)

    for i_r, rec in enumerate(recs):
        ax = axes[0, i_r]
        rec_str = rec_name_str(recs, grouped) if grouped else rec
        gflag = group_flag_str(grouped)
        ks_dir = ks_output_dir(data_root, day, tower, np_num, rec_str, cfg.ks_version)

        ks_file = ks_dir / "cluster_KSLabel.tsv"
        if not ks_file.exists():
            for name in ("cluster_group.tsv", "cluster_groups.csv"):
                candidate = ks_dir / name
                if candidate.exists():
                    ks_file = candidate
                    break

        cids, _ = read_cluster_groups(ks_file)
        my_clus = cids + 1

        # Load NPclu for channel info
        npclu_h5 = data_root / day / rec / f"rec{rec}.{tower}.{np_num}.{gflag}.NPclu.h5"
        npclu_mat = data_root / day / rec / f"rec{rec}.{tower}.{np_num}.{gflag}.NPclu.mat"

        if npclu_h5.exists():
            with h5py.File(npclu_h5, "r") as f:
                ch_ids = np.array(f["clu_info"])[:, 1]
        elif npclu_mat.exists():
            npclu_data = load_mat(npclu_mat)
            clu_info = npclu_data.get("Clu_info", np.empty((0, 2)))
            ch_ids = np.atleast_2d(clu_info)[:, 1] if len(clu_info) > 0 else np.array([])
        else:
            ch_ids = np.array([])

        # Get depth info
        np_elec = get_np_chan_depth_info(day, rec, np_num, tower, data_root)

        bn = (-300, 500)
        t_val = np.arange(bn[0], bn[1] + 1)
        n_time_bins = len(t_val)
        n_clus = len(my_clus)
        psth_matrix = np.zeros((n_clus, n_time_bins))

        grouped_rec_name = rec_str if grouped else None

        for i_unit, clu in enumerate(my_clus):
            raster_file = raster_data_filename(
                data_root, day, rec, tower, np_num, int(clu), gflag,
                grouped_rec_name=grouped_rec_name,
                ks_version=cfg.ks_version,
                ext=".h5",
            )
            raster_file_mat = raster_file.with_suffix(".mat")

            spike_clu, rt = _load_raster_data(raster_file, raster_file_mat)
            if spike_clu is None or len(spike_clu) == 0:
                continue

            _, sorted_sp = sort_spikes_by_rt(rt, spike_clu)
            rate, _ = psth(sorted_sp, bn, smoothing=10)

            # Median filter and normalize
            from scipy.ndimage import median_filter
            rate = median_filter(rate, size=3)
            rate_sub = rate - np.min(rate)
            range_fr = np.max(rate_sub) - np.min(rate_sub)
            if range_fr > 0:
                rate_norm = rate_sub / range_fr
                max_abs = np.max(np.abs(rate_norm))
                if max_abs > 0:
                    rate_norm = rate_norm / max_abs
            else:
                rate_norm = rate_sub

            if len(rate_norm) >= n_time_bins:
                psth_matrix[i_unit, :] = rate_norm[:n_time_bins]

        # Normalize full matrix
        max_val = np.max(psth_matrix)
        if max_val > 0:
            psth_matrix = psth_matrix / max_val

        # Smooth
        psth_matrix = gaussian_filter(psth_matrix, sigma=[0.001, 4])

        # Sort by depth
        clus_depth = _get_cluster_depths(ch_ids, np_elec)
        sort_idx = np.argsort(clus_depth)

        sorted_psth = psth_matrix[sort_idx, :]
        sorted_psth = np.nan_to_num(sorted_psth)

        # Plot
        try:
            from cmcrameri import cm
            cmap = cm.roma_r
        except ImportError:
            cmap = "RdBu_r"

        ax.imshow(
            sorted_psth, aspect="auto",
            extent=[bn[0], bn[1], 0, n_clus],
            cmap=cmap, origin="lower",
        )
        ax.set_xlabel("Time (ms)")
        ax.set_ylabel("Probe Depth")
        ax.set_yticks([])
        ax.set_title(f"Firing Rate - Rec: {rec}")

    fig.suptitle(f"Day {day} NP{np_num}")
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        logger.info("Saved figure: %s", save_path)

    if show:
        plt.show()

    return fig


def _load_raster_data(h5_path: Path, mat_path: Path):
    """Load spike_clu and RT from either HDF5 or .mat file."""
    if h5_path.exists():
        with h5py.File(h5_path, "r") as f:
            if "spike_clu" not in f:
                return None, np.array([])
            grp = f["spike_clu"]
            spike_clu = [np.array(grp[k]) for k in sorted(grp.keys())]
            rt = np.array(f["rt"]) if "rt" in f else np.array([])
        return spike_clu, rt
    elif mat_path.exists():
        data = load_mat(mat_path)
        rd = data.get("RasterData")
        if rd is None:
            return None, np.array([])
        if isinstance(rd, dict):
            spike_clu = rd.get("SpikeClu", [])
            rt = np.atleast_1d(rd.get("RT", []))
        elif hasattr(rd, "SpikeClu"):
            spike_clu = rd.SpikeClu
            rt = np.atleast_1d(getattr(rd, "RT", []))
        else:
            return None, np.array([])
        # Convert cell array to list
        if isinstance(spike_clu, np.ndarray) and spike_clu.dtype == object:
            spike_clu = [np.atleast_1d(s) if s is not None else np.array([]) for s in spike_clu.flat]
        elif not isinstance(spike_clu, list):
            spike_clu = [spike_clu]
        return spike_clu, rt
    return None, np.array([])


def _get_cluster_depths(ch_ids: np.ndarray, np_elec) -> np.ndarray:
    """Map channel IDs to probe depths."""
    depths = np.zeros(len(ch_ids))
    if len(np_elec.chan_id) == 0 or len(np_elec.depth) == 0:
        return depths
    for i, ch_id in enumerate(ch_ids):
        idx = np.where(np_elec.chan_id == ch_id)[0]
        if len(idx) > 0:
            depths[i] = np_elec.depth[idx[0]]
    return depths


def _get_valid_recs(data_root: Path, day: str) -> list[str]:
    """Get valid recording numbers from Excel metadata."""
    excel_file = data_root / "excel" / "valid_recordings.xlsx"
    if excel_file.exists():
        import pandas as pd
        df = pd.read_excel(excel_file)
        return df.loc[df["Day"] == day, "Rec"].tolist()
    # Fallback: list recording directories
    from mind_snag.utils.experiment import dayrecs
    return dayrecs(day, data_root)
