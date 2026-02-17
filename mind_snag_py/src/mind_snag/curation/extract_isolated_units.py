"""Identify isolated units from SortData and update NPclu.

Ports extract_isolated_units.m. Scans SortData files for units
marked as isolated (unit_iso == 1), extracts their spikes, and
saves iso_clu_info back into the NPclu file.
"""

from __future__ import annotations

import logging
from pathlib import Path

import h5py
import numpy as np

from mind_snag.config import MindSnagConfig
from mind_snag.io.mat_reader import load_mat
from mind_snag.io.hdf5_writer import write_hdf5
from mind_snag.utils.paths import (
    rec_name_str, group_flag_str, sort_data_filename, npclu_filename,
)

logger = logging.getLogger(__name__)


def extract_isolated_units(
    cfg: MindSnagConfig,
    day: str,
    recs: list[str],
    tower: str,
    np_num: int,
    grouped: bool,
) -> None:
    """Identify isolated units and update NPclu with isolation info.

    Parameters
    ----------
    cfg : pipeline configuration
    day : recording date (YYMMDD)
    recs : list of recording numbers
    tower : recording setup name
    np_num : probe number
    grouped : whether recordings are concatenated
    """
    cfg.validate()
    data_root = cfg.data_root

    rec_str = rec_name_str(recs, grouped)
    gflag = group_flag_str(grouped)
    grouped_rec_name = rec_str if grouped else None

    n_r = len(recs) if grouped else 1

    for i_r in range(n_r):
        rec = recs[i_r]

        # Load NPclu
        npclu_h5 = data_root / day / rec / f"rec{rec}.{tower}.{np_num}.{gflag}.NPclu.h5"
        npclu_mat = data_root / day / rec / f"rec{rec}.{tower}.{np_num}.{gflag}.NPclu.mat"

        if npclu_h5.exists():
            npclu_data = _load_npclu_h5(npclu_h5)
        elif npclu_mat.exists():
            npclu_data = _load_npclu_mat(npclu_mat)
        else:
            logger.warning("NPclu not found for rec %s", rec)
            continue

        spike_times = npclu_data["spike_times"]
        cluster_ids = npclu_data["cluster_ids"]
        clu_info = npclu_data["clu_info"]

        unique_clus = np.unique(cluster_ids).astype(int)
        iso_clu_ids: list[int] = []

        for clu_id in unique_clus:
            sort_file = sort_data_filename(
                data_root, day, rec, tower, np_num, int(clu_id), gflag,
                grouped_rec_name=grouped_rec_name,
                ks_version=cfg.ks_version,
                ext=".h5",
            )
            # Also try .mat
            sort_file_mat = sort_file.with_suffix(".mat")

            if sort_file.exists():
                with h5py.File(sort_file, "r") as f:
                    if "frame_0000" in f:
                        unit_iso = f["frame_0000"].attrs.get("unit_iso", 0)
                    else:
                        unit_iso = 0
                if unit_iso == 1:
                    iso_clu_ids.append(int(clu_id))
            elif sort_file_mat.exists():
                sd = load_mat(sort_file_mat)
                sort_data = sd.get("SortData")
                if sort_data is not None:
                    ui = _get_unit_iso(sort_data)
                    if ui == 1:
                        iso_clu_ids.append(int(clu_id))
            else:
                logger.debug("SortData not found: %s", sort_file)

        # Build isolated spike data
        iso_mask = np.isin(cluster_ids, iso_clu_ids)
        iso_spike_times = spike_times[iso_mask]
        iso_cluster_ids = cluster_ids[iso_mask]

        # Build iso_clu_info
        iso_clu_info = np.array(
            [[c, clu_info[clu_info[:, 0] == c, 1][0]]
             for c in iso_clu_ids if np.any(clu_info[:, 0] == c)],
            dtype=np.int64,
        ).reshape(-1, 2) if iso_clu_ids else np.empty((0, 2), dtype=np.int64)

        # Save updated NPclu
        out_path = data_root / day / rec / f"rec{rec}.{tower}.{np_num}.{gflag}.NPclu.h5"
        _update_npclu_with_iso(out_path, npclu_data, iso_spike_times, iso_cluster_ids, iso_clu_info)

        logger.info("Saved %d isolated units for rec %s", len(iso_clu_ids), rec)


def _load_npclu_h5(path: Path) -> dict:
    """Load NPclu from HDF5."""
    with h5py.File(path, "r") as f:
        return {
            "spike_times": np.array(f["spike_times"]),
            "cluster_ids": np.array(f["cluster_ids"]),
            "templates": np.array(f["templates"]),
            "clu_info": np.array(f["clu_info"]),
            "ks_clu_info": np.array(f["ks_clu_info"]),
            "pc_feat": np.array(f["pc_feat"]) if "pc_feat" in f else None,
            "temp_scaling_amps": np.array(f["temp_scaling_amps"]),
            "ks_version": int(f.attrs.get("ks_version", 4)),
        }


def _load_npclu_mat(path: Path) -> dict:
    """Load NPclu from .mat file."""
    data = load_mat(path)
    npclu = data.get("NPclu", np.array([]))
    return {
        "spike_times": npclu[:, 0] if len(npclu) > 0 else np.array([]),
        "cluster_ids": npclu[:, 1].astype(np.int64) if len(npclu) > 0 else np.array([]),
        "templates": data.get("NPtemplate", np.array([])),
        "clu_info": np.atleast_2d(data.get("Clu_info", np.empty((0, 2)))).astype(np.int64),
        "ks_clu_info": np.atleast_2d(data.get("KSclu_info", np.empty((0, 2)))).astype(np.int64),
        "pc_feat": data.get("pcFeat"),
        "temp_scaling_amps": data.get("tempScalingAmps", np.array([])),
        "ks_version": int(data.get("KSversion", 4)),
    }


def _get_unit_iso(sort_data) -> int:
    """Extract UnitIso from a MATLAB SortData struct."""
    if isinstance(sort_data, dict):
        return int(sort_data.get("UnitIso", 0))
    if isinstance(sort_data, np.ndarray) and sort_data.size > 0:
        first = sort_data.flat[0]
        if hasattr(first, "UnitIso"):
            return int(first.UnitIso)
        if isinstance(first, dict):
            return int(first.get("UnitIso", 0))
    if hasattr(sort_data, "UnitIso"):
        val = sort_data.UnitIso
        return int(val.flat[0]) if isinstance(val, np.ndarray) else int(val)
    return 0


def _update_npclu_with_iso(
    path: Path, npclu_data: dict,
    iso_spike_times: np.ndarray, iso_cluster_ids: np.ndarray,
    iso_clu_info: np.ndarray,
) -> None:
    """Write updated NPclu with isolation data."""
    data = {
        "spike_times": npclu_data["spike_times"],
        "cluster_ids": npclu_data["cluster_ids"],
        "templates": npclu_data["templates"],
        "clu_info": npclu_data["clu_info"],
        "ks_clu_info": npclu_data["ks_clu_info"],
        "temp_scaling_amps": npclu_data["temp_scaling_amps"],
        "iso_spike_times": iso_spike_times,
        "iso_cluster_ids": iso_cluster_ids,
        "iso_clu_info": iso_clu_info,
    }
    if npclu_data.get("pc_feat") is not None:
        data["pc_feat"] = npclu_data["pc_feat"]

    write_hdf5(
        path, data,
        attrs={"ks_version": npclu_data.get("ks_version", 4)},
    )
