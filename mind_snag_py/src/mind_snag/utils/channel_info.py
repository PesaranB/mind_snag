"""Determine best/worst channel per cluster and get channel depth info.

Ports clus_channel_infor.m and getNP_chanDepthInfo.m.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from mind_snag.io.ks_loader import load_ks_dir
from mind_snag.io.cluster_groups import read_cluster_groups
from mind_snag.io.mat_reader import load_mat
from mind_snag.utils.experiment import load_experiment
from mind_snag.utils.paths import ks_output_dir, rec_name_str


@dataclass
class NPElecInfo:
    """Channel depth and position info for a Neuropixel probe."""

    chan_id: NDArray[np.int64] = field(default_factory=lambda: np.array([], dtype=np.int64))
    depth: NDArray[np.float64] = field(default_factory=lambda: np.array([], dtype=np.float64))
    row: NDArray[np.int64] = field(default_factory=lambda: np.array([], dtype=np.int64))
    col: NDArray[np.int64] = field(default_factory=lambda: np.array([], dtype=np.int64))
    x_coord: NDArray[np.float64] = field(default_factory=lambda: np.array([], dtype=np.float64))
    y_coord: NDArray[np.float64] = field(default_factory=lambda: np.array([], dtype=np.float64))
    elec_num: NDArray[np.int64] = field(default_factory=lambda: np.array([], dtype=np.int64))


def get_np_chan_depth_info(
    day: str, rec: str, np_num: int, tower: str, data_root: Path,
) -> NPElecInfo:
    """Get channel depth and position info for a Neuropixel probe.

    Ports getNP_chanDepthInfo.m.

    Parameters
    ----------
    day : recording date (YYMMDD)
    rec : recording number
    np_num : probe number
    tower : recording setup name
    data_root : root data directory

    Returns
    -------
    NPElecInfo with channel positions
    """
    experiment = load_experiment(day, rec, data_root)
    info = NPElecInfo()

    if experiment is None:
        return info

    # Find microdrive matching tower name
    hardware = experiment.get("hardware", {}) if isinstance(experiment, dict) else {}
    drives = hardware.get("microdrive", [])
    if not isinstance(drives, list):
        drives = [drives]

    drive = None
    for d in drives:
        if isinstance(d, dict) and d.get("name") == tower:
            drive = d
            break

    if drive is None:
        return info

    np_electrodes = drive.get("electrodes", [])

    # Load channel info
    chan_info_file = data_root / day / rec / f"rec{rec}.{tower}.{np_num}.channel_info.mat"
    if not chan_info_file.exists():
        return info

    chan_data = load_mat(chan_info_file)
    channel_info = chan_data.get("channel_info")
    if channel_info is None:
        return info

    # Extract electrode numbers
    if isinstance(channel_info, np.ndarray):
        # struct array from scipy
        if hasattr(channel_info, "electrode"):
            elec_num = np.atleast_1d(channel_info.electrode).astype(np.int64)
        elif isinstance(channel_info, dict):
            elec_num = np.atleast_1d(channel_info.get("electrode", [])).astype(np.int64)
        else:
            elec_num = np.array([], dtype=np.int64)
    elif isinstance(channel_info, dict):
        elec_num = np.atleast_1d(channel_info.get("electrode", [])).astype(np.int64)
    elif isinstance(channel_info, list):
        elec_num = np.array([c.get("electrode", 0) if isinstance(c, dict) else 0 for c in channel_info], dtype=np.int64)
    else:
        elec_num = np.array([], dtype=np.int64)

    info.elec_num = elec_num

    # Extract position info from electrodes metadata
    if isinstance(np_electrodes, list) and len(np_electrodes) > 0 and len(elec_num) > 0:
        chan_ids = []
        depths = []
        rows = []
        cols = []
        x_coords = []
        y_coords = []
        for en in elec_num:
            idx = int(en)
            if 0 <= idx < len(np_electrodes):
                elec = np_electrodes[idx]
                if isinstance(elec, dict):
                    chan_ids.append(elec.get("channelid", 0))
                    pos = elec.get("position", {})
                    if isinstance(pos, dict):
                        depths.append(pos.get("depth", 0))
                        rows.append(pos.get("within_probe_row", 0))
                        cols.append(pos.get("within_probe_col", 0))
                        x_coords.append(pos.get("within_probe_x", 0))
                        y_coords.append(pos.get("within_probe_y", 0))

        if chan_ids:
            info.chan_id = np.array(chan_ids, dtype=np.int64)
            info.depth = np.array(depths, dtype=np.float64)
            info.row = np.array(rows, dtype=np.int64)
            info.col = np.array(cols, dtype=np.int64)
            info.x_coord = np.array(x_coords, dtype=np.float64)
            info.y_coord = np.array(y_coords, dtype=np.float64)

    return info


def clus_channel_info(
    cfg: Any,
    day: str,
    recs: list[str],
    tower: str,
    np_num: int,
    grouped: bool,
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Get best (max energy) and worst (min energy) channel per cluster.

    Ports clus_channel_infor.m. For each cluster, determines the channel
    with highest waveform energy (max_site) and lowest energy (min_site),
    weighted by PC feature coverage.

    Parameters
    ----------
    cfg : MindSnagConfig
    day : recording date
    recs : list of recording numbers
    tower : recording setup name
    np_num : probe number
    grouped : whether recordings are concatenated

    Returns
    -------
    max_site : array of best channel indices (one per cluster)
    min_site : array of worst channel indices (one per cluster)
    """
    data_root = cfg.data_root
    rec_str = rec_name_str(recs, grouped)
    ks_dir = ks_output_dir(data_root, day, tower, np_num, rec_str, cfg.ks_version)

    sp = load_ks_dir(ks_dir, exclude_noise=False)
    pc_feat_ind = sp.pc_feat_ind
    spike_temps = sp.clu
    temps = sp.temps

    # Read cluster labels
    ks_file = ks_dir / "cluster_KSLabel.tsv"
    if not ks_file.exists():
        for name in ("cluster_group.tsv", "cluster_groups.csv"):
            candidate = ks_dir / name
            if candidate.exists():
                ks_file = candidate
                break

    cids, _ = read_cluster_groups(ks_file)
    # MATLAB uses 1-indexed cluster IDs internally; we stay 0-indexed
    # but the logic references by position in cids array

    alpha = 1.0
    min_pc_threshold = 0.1

    max_site_list: list[int] = []
    min_site_list: list[int] = []

    for clu_id in cids:
        my_spikes = np.where(spike_temps == clu_id)[0]
        if len(my_spikes) == 0:
            max_site_list.append(0)
            min_site_list.append(0)
            continue

        # Template waveform for this cluster
        this_clu_temp = temps[clu_id]  # [nTimePoints x nChannels]
        tmp_ind = pc_feat_ind[clu_id]  # local channel indices (0-indexed)
        this_clu_wfs = this_clu_temp[:, tmp_ind]  # [nTimePoints x nLocalChans]
        ptp_energy = np.sum(this_clu_wfs ** 2, axis=0)

        # Non-zero PC ratios
        my_pc_feat = sp.pc_feat[my_spikes, :3, :] if sp.pc_feat is not None else None
        n_local = len(tmp_ind)
        non_zeros_pc_ratios = np.zeros(n_local)
        if my_pc_feat is not None:
            for ch in range(min(n_local, my_pc_feat.shape[2])):
                pc_ch = my_pc_feat[:, :, ch]
                zero_mask = np.all(pc_ch == 0, axis=1)
                non_zeros_pc_ratios[ch] = 1.0 - np.sum(zero_mask) / pc_ch.shape[0]

        # Normalize
        max_energy = np.max(ptp_energy) if np.max(ptp_energy) > 0 else 1.0
        ptp_norm = ptp_energy / max_energy
        max_nzr = np.max(non_zeros_pc_ratios) if np.max(non_zeros_pc_ratios) > 0 else 1.0
        nzr_norm = non_zeros_pc_ratios / max_nzr

        combined_score = alpha * ptp_norm + (1 - alpha) * nzr_norm
        best_idx = int(np.argmax(combined_score))

        # Check if best channel has sufficient PC coverage
        if non_zeros_pc_ratios[best_idx] < 0.5:
            eligible = np.where(non_zeros_pc_ratios >= 0.5)[0]
            if len(eligible) > 0:
                best_idx = eligible[int(np.argmax(combined_score[eligible]))]

        max_site_list.append(int(tmp_ind[best_idx]))

        # Worst channel
        worst_idx = int(np.argmin(ptp_energy))
        if non_zeros_pc_ratios[worst_idx] < min_pc_threshold:
            eligible = np.where(
                (non_zeros_pc_ratios >= min_pc_threshold) & (ptp_energy > 0)
            )[0]
            if len(eligible) > 0:
                worst_idx = eligible[int(np.argmin(ptp_energy[eligible]))]

        min_site_list.append(int(tmp_ind[worst_idx]))

    return np.array(max_site_list, dtype=np.int64), np.array(min_site_list, dtype=np.int64)
