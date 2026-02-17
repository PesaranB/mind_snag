"""Extract spike times from Kilosort output with drift correction.

Ports extract_spikes.m. Loads KS results, applies two-stage drift correction
(AP -> NIDQ -> recording timebase), and saves structured cluster data.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from mind_snag.config import MindSnagConfig
from mind_snag.io.ks_loader import load_ks_dir
from mind_snag.io.cluster_groups import read_cluster_groups
from mind_snag.io.mat_reader import load_mat
from mind_snag.io.hdf5_writer import write_npclu_h5
from mind_snag.utils.channel_info import clus_channel_info
from mind_snag.utils.paths import (
    ks_output_dir, rec_name_str, group_flag_str, group_rec_dir,
)

logger = logging.getLogger(__name__)


def extract_spikes(
    cfg: MindSnagConfig,
    day: str,
    recs: list[str],
    tower: str,
    np_num: int,
    grouped: bool,
) -> None:
    """Extract spike times with drift correction from Kilosort output.

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
    ks_dir = ks_output_dir(data_root, day, tower, np_num, rec_str, cfg.ks_version)

    if not ks_dir.exists():
        raise FileNotFoundError(
            f"Kilosort output directory not found: {ks_dir}\nRun run_kilosort4 first."
        )

    # Load KS output
    sp = load_ks_dir(ks_dir, exclude_noise=False)
    max_site, _ = clus_channel_info(cfg, day, recs, tower, np_num, grouped)

    # Load group file
    grp_dir = group_rec_dir(data_root, day, tower, np_num)
    group_file = grp_dir / f"spike_sorting_rec_groups_{rec_str}.mat"

    if grouped:
        _extract_grouped(cfg, sp, max_site, day, recs, tower, np_num, gflag, ks_dir, data_root)
    else:
        _extract_single(cfg, sp, max_site, day, recs[0], tower, np_num, gflag, ks_dir, data_root, group_file)


def _apply_drift_correction(
    spike_times: np.ndarray,
    w_nidq: np.ndarray,
    w_rec: np.ndarray,
) -> np.ndarray:
    """Apply two-stage drift correction: AP -> NIDQ -> recording timebase.

    Parameters
    ----------
    spike_times : raw spike times
    w_nidq : [intercept, slope] for AP -> NIDQ correction
    w_rec : [intercept, slope] for NIDQ -> recording correction

    Returns
    -------
    Drift-corrected spike times
    """
    st_nidq = w_nidq[0] + w_nidq[1] * spike_times
    return w_rec[0] + w_rec[1] * st_nidq


def _extract_grouped(
    cfg, sp, max_site, day, recs, tower, np_num, gflag, ks_dir, data_root,
):
    """Extract spikes for grouped (concatenated) recordings."""
    theo_offset = 0.0

    for i_r, rec in enumerate(recs):
        rec_dir = data_root / day / rec
        output_dir = data_root / day / rec
        output_dir.mkdir(parents=True, exist_ok=True)

        # Load metadata
        ap_meta_file = rec_dir / f"rec{rec}.{tower}.{np_num}.ap_meta.mat"
        nidq_meta_file = rec_dir / f"rec{rec}.nidq_meta.mat"
        if not ap_meta_file.exists():
            raise FileNotFoundError(f"AP meta file not found: {ap_meta_file}")

        ap_meta_data = load_mat(ap_meta_file)
        ap_meta = ap_meta_data.get("ap_meta", {})
        nidq_meta_data = load_mat(nidq_meta_file)
        nidq_meta = nidq_meta_data.get("nidq_meta", {})

        nsamp = _get_field(ap_meta, "nsamp")
        fs = _get_field(ap_meta, "Fs")
        theo_dur = nsamp / fs

        # Select spikes in this recording's time window
        mask = (sp.st <= theo_offset + theo_dur) & (sp.st > theo_offset)
        st_select = sp.st[mask] - theo_offset

        # Drift correction
        w_nidq = np.atleast_1d(_get_field(ap_meta, "nidq_drift_model_weights"))
        w_rec = np.atleast_1d(_get_field(nidq_meta, "rec_drift_model_weights"))

        new_spike_times = _apply_drift_correction(st_select, w_nidq, w_rec)
        new_spike_templates = sp.spike_templates[mask]

        theo_offset += theo_dur

        # Build NPclu (1-indexed cluster IDs for MATLAB compat)
        npclu = np.column_stack([new_spike_times, new_spike_templates + 1])
        templates = sp.temps
        pc_feat = sp.pc_feat[mask, :3, :] if sp.pc_feat is not None else None
        temp_scaling = sp.temp_scaling_amps[mask]

        clu_id = np.unique(sp.clu) + 1
        clu_info = np.column_stack([clu_id, max_site[: len(clu_id)]])

        # KS good units
        ks_file = ks_dir / "cluster_KSLabel.tsv"
        cids, cgs = read_cluster_groups(ks_file)
        ks_clu_id = cids[cgs == 2] + 1
        ks_mask = np.isin(clu_info[:, 0], ks_clu_id)
        ks_clu_info = clu_info[ks_mask]

        # Save
        out_file = output_dir / f"rec{rec}.{tower}.{np_num}.{gflag}.NPclu.h5"
        logger.info("Saving: %s", out_file)
        write_npclu_h5(
            out_file,
            spike_times=npclu[:, 0],
            cluster_ids=npclu[:, 1].astype(np.int64),
            templates=templates,
            clu_info=clu_info,
            ks_clu_info=ks_clu_info,
            pc_feat=pc_feat,
            temp_scaling_amps=temp_scaling,
            ks_version=cfg.ks_version,
        )


def _extract_single(
    cfg, sp, max_site, day, rec, tower, np_num, gflag, ks_dir, data_root, group_file,
):
    """Extract spikes for a single (non-grouped) recording."""
    rec_dir = data_root / day / rec

    # Try to load AP meta with NP number, fallback without
    ap_meta_file = rec_dir / f"rec{rec}.{tower}.{np_num}.ap_meta.mat"
    nidq_meta_file = rec_dir / f"rec{rec}.nidq_meta.mat"

    if not ap_meta_file.exists():
        ap_meta_file = rec_dir / f"rec{rec}.{tower}.ap_meta.mat"

    ap_meta_data = load_mat(ap_meta_file)
    ap_meta = ap_meta_data.get("ap_meta", {})
    nidq_meta_data = load_mat(nidq_meta_file)
    nidq_meta = nidq_meta_data.get("nidq_meta", {})

    nsamp = _get_field(ap_meta, "nsamp")
    fs = _get_field(ap_meta, "Fs")
    theo_dur = nsamp / fs

    mask = (sp.st < theo_dur) & (sp.st > 0)
    st_select = sp.st[mask]

    # Drift correction
    w_nidq = np.atleast_1d(_get_field(ap_meta, "nidq_drift_model_weights"))
    w_rec = np.atleast_1d(_get_field(nidq_meta, "rec_drift_model_weights"))

    new_spike_times = _apply_drift_correction(st_select, w_nidq, w_rec)
    new_spike_templates = sp.spike_templates[mask]

    npclu = np.column_stack([new_spike_times, new_spike_templates + 1])
    templates = sp.temps
    pc_feat = sp.pc_feat[mask, :3, :] if sp.pc_feat is not None else None
    temp_scaling = sp.temp_scaling_amps[mask]

    clu_id = np.unique(sp.clu) + 1
    clu_info = np.column_stack([clu_id, max_site[: len(clu_id)]])

    # KS good units
    ks_file = ks_dir / "cluster_KSLabel.tsv"
    cids, cgs = read_cluster_groups(ks_file)
    ks_clu_id = cids[cgs == 2] + 1
    ks_mask = np.isin(clu_info[:, 0], ks_clu_id)
    ks_clu_info = clu_info[ks_mask]

    output_dir = data_root / day / rec
    output_dir.mkdir(parents=True, exist_ok=True)

    out_file = output_dir / f"rec{rec}.{tower}.{np_num}.{gflag}.NPclu.h5"
    logger.info("Saving: %s", out_file)
    write_npclu_h5(
        out_file,
        spike_times=npclu[:, 0],
        cluster_ids=npclu[:, 1].astype(np.int64),
        templates=templates,
        clu_info=clu_info,
        ks_clu_info=ks_clu_info,
        pc_feat=pc_feat,
        temp_scaling_amps=temp_scaling,
        ks_version=cfg.ks_version,
    )


def _get_field(obj, name, default=0):
    """Get a field from a dict or scipy mat_struct."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)
