"""Compute PC features and isolation scores per cluster.

Ports compute_isolation.m. For each cluster, extracts PC features on the
max-amplitude channel, segments the recording into time windows, and computes
isolation metrics (signal-to-noise score) against nearby noise channels.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from mind_snag.config import MindSnagConfig
from mind_snag.io.ks_loader import load_ks_dir
from mind_snag.io.cluster_groups import read_cluster_groups
from mind_snag.io.mat_reader import load_mat
from mind_snag.io.hdf5_writer import write_sort_data_h5
from mind_snag.utils.channel_info import clus_channel_info
from mind_snag.utils.paths import (
    ks_output_dir, rec_name_str, group_flag_str, sort_data_filename,
)

logger = logging.getLogger(__name__)


def compute_isolation(
    cfg: MindSnagConfig,
    day: str,
    recs: list[str],
    tower: str,
    np_num: int,
    grouped: bool,
    clu_ids: list[int] | None = None,
) -> None:
    """Compute isolation scores for all (or specific) clusters.

    Parameters
    ----------
    cfg : pipeline configuration
    day : recording date (YYMMDD)
    recs : list of recording numbers
    tower : recording setup name
    np_num : probe number
    grouped : whether recordings are concatenated
    clu_ids : optional list of specific cluster IDs (0-indexed)
    """
    cfg.validate()
    data_root = cfg.data_root
    iso_win = cfg.isolation.window_sec

    rec_str = rec_name_str(recs, grouped)
    gflag = group_flag_str(grouped)
    ks_dir = ks_output_dir(data_root, day, tower, np_num, rec_str, cfg.ks_version)

    sp = load_ks_dir(ks_dir, exclude_noise=False)
    max_site, min_site = clus_channel_info(cfg, day, recs, tower, np_num, grouped)

    ks_file = ks_dir / "cluster_KSLabel.tsv"
    cids, cgs = read_cluster_groups(ks_file)
    good_clus = set(cids[cgs == 2].tolist())

    pc_feat_ind = sp.pc_feat_ind

    n_r = len(recs) if grouped else 1

    for i_r in range(n_r):
        rec = recs[i_r]

        if grouped:
            npclu_path = data_root / day / rec / f"rec{rec}.{tower}.{np_num}.{gflag}.NPclu.h5"
            # Try HDF5 first, fall back to .mat
            if npclu_path.exists():
                import h5py
                with h5py.File(npclu_path, "r") as f:
                    rec_spike_temps = np.array(f["cluster_ids"])
                    rec_spike_times = np.array(f["spike_times"])
                    temp_scaling = np.array(f["temp_scaling_amps"])
                    pc_feat = np.array(f["pc_feat"]) if "pc_feat" in f else None
            else:
                npclu_path_mat = data_root / day / rec / f"rec{rec}.{tower}.{np_num}.{gflag}.NPclu.mat"
                npclu_data = load_mat(npclu_path_mat)
                npclu = npclu_data.get("NPclu", np.array([]))
                rec_spike_temps = npclu[:, 1] if len(npclu) > 0 else np.array([])
                rec_spike_times = npclu[:, 0] if len(npclu) > 0 else np.array([])
                temp_scaling = npclu_data.get("tempScalingAmps", sp.temp_scaling_amps)
                pc_feat = npclu_data.get("pcFeat", sp.pc_feat)
        else:
            rec_spike_temps = sp.clu
            rec_spike_times = sp.st
            temp_scaling = sp.temp_scaling_amps
            pc_feat = sp.pc_feat

        temps = sp.temps

        # Determine which clusters to process
        if clu_ids is not None:
            my_clus = [c + 1 for c in clu_ids]  # to 1-indexed
        else:
            my_clus = (cids + 1).tolist()

        grouped_rec_name = rec_str if grouped else None
        ks_save = "KSsave_KS4" if cfg.ks_version == 4 else ""

        for clu in my_clus:
            # Find spikes for this cluster
            if grouped:
                my_spikes = np.where(rec_spike_temps == clu)[0]
            else:
                my_spikes = np.where(rec_spike_temps == clu - 1)[0]

            frames: list[dict] = []

            if len(my_spikes) > 0 and max_site is not None and clu - 1 < len(max_site):
                spike_ch_ind = max_site[clu - 1]

                # Template waveform
                if clu - 1 < temps.shape[0] and spike_ch_ind < temps.shape[2]:
                    my_spike_wf = temps[clu - 1, :, spike_ch_ind]
                else:
                    my_spike_wf = np.full(61, np.nan)

                # PC features for this cluster's channel
                if pc_feat_ind is not None and pc_feat is not None and clu - 1 < len(pc_feat_ind):
                    tmp_ind = pc_feat_ind[clu - 1]
                    pc_ch_idx = np.where(tmp_ind == spike_ch_ind)[0]
                    my_amp = np.tile(
                        temp_scaling[my_spikes].reshape(-1, 1, 1),
                        (1, 3, 1),
                    )
                    if len(pc_ch_idx) > 0:
                        my_pc_feat = pc_feat[my_spikes, :3, pc_ch_idx[0]:pc_ch_idx[0]+1] * my_amp
                    else:
                        my_pc_feat = np.zeros((len(my_spikes), 3, 1))
                else:
                    my_pc_feat = np.zeros((len(my_spikes), 3, 1))

                # Noise channel
                noise_ch_ind = min_site[clu - 1] if clu - 1 < len(min_site) else spike_ch_ind
                if clu - 1 < temps.shape[0] and noise_ch_ind < temps.shape[2]:
                    noise_wf = temps[clu - 1, :, noise_ch_ind]
                else:
                    noise_wf = np.full(61, np.nan)

                if pc_feat_ind is not None and pc_feat is not None and clu - 1 < len(pc_feat_ind):
                    tmp_ind = pc_feat_ind[clu - 1]
                    noise_ch_idx = np.where(tmp_ind == noise_ch_ind)[0]
                    if len(noise_ch_idx) > 0:
                        my_pc_noise = pc_feat[my_spikes, :3, noise_ch_idx[0]:noise_ch_idx[0]+1] * my_amp
                    else:
                        my_pc_noise = np.zeros_like(my_pc_feat)
                else:
                    my_pc_noise = np.zeros_like(my_pc_feat)

                my_spike_times = rec_spike_times[my_spikes]

                # Find other clusters on same channel
                other_clus_mask = max_site == max_site[clu - 1]
                other_clus = np.where(other_clus_mask)[0]
                other_clus = other_clus[other_clus != (clu - 1)]

                # Segment into time windows
                if len(rec_spike_times) > 0:
                    frac_end = int(np.ceil(np.max(rec_spike_times) / iso_win)) * iso_win
                    frac = np.arange(0, frac_end + iso_win, iso_win)
                    n_frames = len(frac) - 1
                else:
                    n_frames = 0

                if n_frames > 0:
                    for i_frame in range(n_frames):
                        ind = np.where(
                            (my_spike_times >= frac[i_frame]) &
                            (my_spike_times <= frac[i_frame + 1])
                        )[0]

                        frame: dict = {
                            "clu_wf": my_spike_wf,
                            "noise_wf": noise_wf,
                            "unit_iso": 0,
                            "clu": int(clu),
                        }

                        if len(ind) > 0:
                            unit_feat = my_pc_feat[ind].squeeze(-1)
                            noise_feat = my_pc_noise[ind].squeeze(-1)
                            frame["unit"] = unit_feat
                            frame["noise"] = noise_feat
                            frame["mean_spike_amp"] = np.mean(unit_feat, axis=0)
                            frame["mean_noise_amp"] = np.mean(noise_feat, axis=0)
                            frame["sd_noise_amp"] = np.std(noise_feat, axis=0, ddof=0)
                            sd = frame["sd_noise_amp"]
                            if sd[0] > 0:
                                frame["score"] = float(
                                    np.abs(frame["mean_spike_amp"][0] - frame["mean_noise_amp"][0]) / sd[0]
                                )
                            else:
                                frame["score"] = 0.0
                        frames.append(frame)
                else:
                    frames.append({
                        "clu_wf": my_spike_wf,
                        "noise_wf": noise_wf,
                        "unit": my_pc_feat.squeeze(-1),
                        "noise": my_pc_noise.squeeze(-1),
                        "unit_iso": 0,
                        "clu": int(clu),
                    })
            else:
                frames.append({
                    "unit_iso": 0,
                    "clu": int(clu),
                })

            # Save
            out_file = sort_data_filename(
                data_root, day, rec, tower, np_num, clu, gflag,
                grouped_rec_name=grouped_rec_name,
                ks_version=cfg.ks_version,
                ext=".h5",
            )
            out_file.parent.mkdir(parents=True, exist_ok=True)
            write_sort_data_h5(out_file, frames)
            logger.info("Saved: %s", out_file)
