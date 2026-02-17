"""Align spikes to behavioral trial events.

Ports extract_rasters.m. Replaces the 250 lines of repetitive try/catch
blocks with a data-driven loop over TaskTypeConfig definitions.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from mind_snag.config import MindSnagConfig
from mind_snag.io.ks_loader import load_ks_dir
from mind_snag.io.cluster_groups import read_cluster_groups
from mind_snag.io.mat_reader import load_mat
from mind_snag.io.hdf5_writer import write_raster_data_h5
from mind_snag.trials.load_trials import load_trials
from mind_snag.trials.trial_spike import trial_np_spike
from mind_snag.trials.task_types import TASK_TYPES, TaskTypeConfig
from mind_snag.utils.channel_info import clus_channel_info
from mind_snag.utils.paths import (
    ks_output_dir, rec_name_str, group_flag_str, raster_data_filename,
)

logger = logging.getLogger(__name__)


def extract_rasters(
    cfg: MindSnagConfig,
    day: str,
    recs: list[str],
    tower: str,
    np_num: int,
    grouped: bool,
    clu_ids: list[int] | None = None,
) -> None:
    """Extract trial-aligned rasters for all (or specific) clusters.

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

    rec_str = rec_name_str(recs, grouped)
    gflag = group_flag_str(grouped)
    ks_dir = ks_output_dir(data_root, day, tower, np_num, rec_str, cfg.ks_version)

    max_site, _ = clus_channel_info(cfg, day, recs, tower, np_num, grouped)

    n_r = len(recs) if grouped else 1

    for i_r in range(n_r):
        rec = recs[i_r]

        sp = load_ks_dir(ks_dir, exclude_noise=False)
        ks_file = ks_dir / "cluster_KSLabel.tsv"

        if grouped:
            npclu_h5 = data_root / day / rec / f"rec{rec}.{tower}.{np_num}.{gflag}.NPclu.h5"
            npclu_mat = data_root / day / rec / f"rec{rec}.{tower}.{np_num}.{gflag}.NPclu.mat"
            if npclu_h5.exists():
                import h5py
                with h5py.File(npclu_h5, "r") as f:
                    spike_temps = np.array(f["cluster_ids"])
            elif npclu_mat.exists():
                npclu_data = load_mat(npclu_mat)
                npclu_arr = npclu_data.get("NPclu", np.array([]))
                spike_temps = npclu_arr[:, 1] if len(npclu_arr) > 0 else np.array([])
            else:
                logger.warning("NPclu not found for rec %s", rec)
                continue
        else:
            spike_temps = sp.clu

        cids, _ = read_cluster_groups(ks_file)
        my_clus = [c + 1 for c in clu_ids] if clu_ids else (cids + 1).tolist()

        # Load trials
        trials = load_trials(day, rec, data_root)

        # Categorize trials by task type
        task_trial_map = _categorize_trials(trials)

        ks_version_flag = cfg.ks_version
        grouped_rec_name = rec_str if grouped else None

        for clu in my_clus:
            if grouped:
                my_spikes = np.where(spike_temps == clu)[0]
            else:
                my_spikes = np.where(spike_temps == clu - 1)[0]

            if len(my_spikes) == 0:
                _save_empty_raster(
                    data_root, day, rec, tower, np_num, clu, gflag,
                    grouped_rec_name, cfg.ks_version,
                )
                continue

            # Extract rasters for each task type using data-driven loop
            all_spikes: list = []
            all_rt: list[float] = []

            for task_cfg in TASK_TYPES:
                task_trials = task_trial_map.get(task_cfg.name, [])
                if not task_trials:
                    continue

                spikes, rt = _extract_task_rasters(
                    task_trials, tower, np_num, clu,
                    task_cfg, data_root, ks_version_flag, grouped,
                )
                all_spikes.extend(spikes)
                all_rt.extend(rt)

            # Extract neighboring clusters
            other_clus = _find_neighbor_clus(max_site, clu)

            # Save
            out_file = raster_data_filename(
                data_root, day, rec, tower, np_num, clu, gflag,
                grouped_rec_name=grouped_rec_name,
                ks_version=cfg.ks_version,
                ext=".h5",
            )
            out_file.parent.mkdir(parents=True, exist_ok=True)
            write_raster_data_h5(
                out_file,
                clu=clu,
                spike_clu=all_spikes,
                rt=np.array(all_rt) if all_rt else None,
                other_clu=np.array(other_clus, dtype=np.int64) if other_clus else None,
            )
            logger.info("Saved: %s", out_file)


def _categorize_trials(trials: list[dict]) -> dict[str, list[dict]]:
    """Categorize trials by task type using TASK_TYPES definitions."""
    result: dict[str, list[dict]] = {}

    for task_cfg in TASK_TYPES:
        result[task_cfg.name] = []

    for trial in trials:
        py_task_type = trial.get("PyTaskType", "")
        matched = False
        for task_cfg in TASK_TYPES:
            if py_task_type in task_cfg.py_task_types:
                result[task_cfg.name].append(trial)
                matched = True
                break
        if not matched and py_task_type == "":
            # Legacy: no PyTaskType, treat as Reach
            result["Reach"].append(trial)

    return result


def _extract_task_rasters(
    trials: list[dict],
    tower: str,
    np_num: int,
    clu: int,
    task_cfg: TaskTypeConfig,
    data_root: Path,
    ks_version: int,
    grouped: bool,
) -> tuple[list, list[float]]:
    """Extract rasters for one task type with primary/fallback events."""
    try:
        spikes = trial_np_spike(
            trials, tower, np_num, clu,
            task_cfg.primary_event, task_cfg.time_window,
            data_root, ks_version, grouped,
        )
        rt = _compute_rt(trials, task_cfg.rt_event, task_cfg.rt_baseline)
    except Exception:
        if task_cfg.fallback_event:
            spikes = trial_np_spike(
                trials, tower, np_num, clu,
                task_cfg.fallback_event, task_cfg.time_window,
                data_root, ks_version, grouped,
            )
            fb_event = task_cfg.rt_fallback_event or task_cfg.rt_event
            fb_base = task_cfg.rt_fallback_baseline or task_cfg.rt_baseline
            rt = _compute_rt(trials, fb_event, fb_base)
        else:
            spikes = [np.array([]) for _ in trials]
            rt = []

    return spikes, rt


def _compute_rt(trials: list[dict], event_field: str, baseline_field: str) -> list[float]:
    """Compute reaction times from trial event fields."""
    if not event_field or not baseline_field:
        return []
    rt = []
    for t in trials:
        ev = t.get(event_field)
        bl = t.get(baseline_field)
        if ev is not None and bl is not None:
            rt.append(float(ev) - float(bl))
        else:
            rt.append(float("nan"))
    return rt


def _find_neighbor_clus(max_site: np.ndarray, clu: int) -> list[int]:
    """Find clusters on the same channel as clu."""
    if clu - 1 >= len(max_site):
        return []
    target_site = max_site[clu - 1]
    neighbors = np.where(max_site == target_site)[0]
    return [int(n + 1) for n in neighbors if n != clu - 1]


def _save_empty_raster(
    data_root, day, rec, tower, np_num, clu, gflag,
    grouped_rec_name, ks_version,
):
    """Save an empty RasterData entry."""
    out_file = raster_data_filename(
        data_root, day, rec, tower, np_num, clu, gflag,
        grouped_rec_name=grouped_rec_name,
        ks_version=ks_version,
        ext=".h5",
    )
    out_file.parent.mkdir(parents=True, exist_ok=True)
    write_raster_data_h5(out_file, clu=clu, spike_clu=[], rt=None)
