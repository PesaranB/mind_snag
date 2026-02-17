"""Save neuron stitching results.

Ports save_stitch_results.m. Saves in both the legacy NPSpike_KS4_Database
format (.m script) and a new HDF5 format.
"""

from __future__ import annotations

import logging
from pathlib import Path

import h5py
import numpy as np

from mind_snag.config import MindSnagConfig
from mind_snag.io.ks_loader import load_ks_dir
from mind_snag.io.mat_reader import load_mat
from mind_snag.types import StitchResult
from mind_snag.utils.paths import ks_output_dir, group_flag_str

logger = logging.getLogger(__name__)


def save_stitch_results(
    cfg: MindSnagConfig,
    result: StitchResult,
    output_dir: str | Path,
    format: str = "both",
) -> Path:
    """Save stitching results.

    Parameters
    ----------
    cfg : pipeline configuration
    result : StitchResult from NeuronStitcher.run()
    output_dir : directory to save results
    format : 'hdf5', 'legacy', or 'both'

    Returns
    -------
    Path to primary output file
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rec_str = "_".join(result.recs)
    primary_path = output_dir / f"stitch_{result.day}_{rec_str}.h5"

    if format in ("hdf5", "both"):
        _save_hdf5(primary_path, result)

    if format in ("legacy", "both"):
        legacy_path = output_dir / f"NPSpike_KS4_Database_{result.day}_{rec_str}.m"
        _save_legacy(legacy_path, cfg, result)

    return primary_path


def _save_hdf5(path: Path, result: StitchResult) -> None:
    """Save stitch results in HDF5 format."""
    with h5py.File(path, "w") as f:
        f.create_dataset("stitch_table", data=result.stitch_table, compression="gzip")
        f.attrs["day"] = result.day
        f.attrs["tower"] = result.tower
        f.attrs["np_num"] = result.np_num
        f.attrs["num_recs"] = len(result.recs)
        for i, rec in enumerate(result.recs):
            f.attrs[f"rec_{i}"] = rec

    logger.info("Saved HDF5 stitch results: %s", path)


def _save_legacy(path: Path, cfg: MindSnagConfig, result: StitchResult) -> None:
    """Save stitch results in legacy NPSpike_KS4_Database .m format."""
    data_root = cfg.data_root
    day = result.day
    recs = result.recs
    tower = result.tower
    np_num = result.np_num
    rec_str = "_".join(recs)
    gflag = "Grouped" if cfg.ks_version == 4 else "NotGrouped"

    # Load channel map
    ks_dir = ks_output_dir(data_root, day, tower, np_num, rec_str, cfg.ks_version)
    sp = load_ks_dir(ks_dir, exclude_noise=False)
    chan_map = sp.chan_map  # 0-indexed

    lines = [
        f"function Session = NPSpike_KS4_Database_{day}_{rec_str}\n",
        "Session = cell(0, 0); ind = 1;\n\n",
    ]

    for i in range(result.stitch_table.shape[0]):
        row = result.stitch_table[i]
        valid_mask = ~np.isnan(row)
        valid_recs = [recs[j] for j in range(len(recs)) if valid_mask[j]]
        valid_clus = row[valid_mask].astype(int)

        recs_str = "', '".join(valid_recs)
        clus_str = " ".join(str(c) for c in valid_clus)

        # Get channels for each cluster
        channels = []
        for clu_id, rec in zip(valid_clus, valid_recs):
            ch = _get_cluster_channel(data_root, day, rec, tower, np_num, gflag, int(clu_id), chan_map)
            channels.append(str(ch))
        channels_str = " ".join(channels)

        lines.append(
            f"Session{{ind}} = {{'{day}', {{'{recs_str}'}}, "
            f"{{'{tower}'}}, {np_num}, [{channels_str}],[{clus_str}], "
            f"ind, '{data_root}', 'NPSpike'}}; ind = ind+1;\n"
        )

    with open(path, "w") as f:
        f.writelines(lines)

    logger.info("Saved legacy stitch results: %s", path)


def _get_cluster_channel(
    data_root: Path, day: str, rec: str, tower: str,
    np_num: int, gflag: str, clu_id: int, chan_map: np.ndarray,
) -> int:
    """Look up the channel for a cluster from NPclu data."""
    for ext in (".h5", ".mat"):
        npclu_path = data_root / day / rec / f"rec{rec}.{tower}.{np_num}.{gflag}.NPclu{ext}"
        if npclu_path.exists():
            if ext == ".h5":
                with h5py.File(npclu_path, "r") as f:
                    clu_info = np.array(f["clu_info"])
            else:
                data = load_mat(npclu_path)
                clu_info = np.atleast_2d(data.get("Clu_info", np.empty((0, 2))))

            idx = np.where(clu_info[:, 0] == clu_id)[0]
            if len(idx) > 0:
                chan_idx = int(clu_info[idx[0], 1])
                if 0 <= chan_idx < len(chan_map):
                    return int(chan_map[chan_idx])
    return 0
