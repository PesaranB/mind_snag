"""Cross-recording neuron identity matching.

Ports stitch_neurons.m. The 4 nested functions that capture parent scope
become methods on the NeuronStitcher class.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from mind_snag.config import MindSnagConfig
from mind_snag.io.ks_loader import load_ks_dir
from mind_snag.io.mat_reader import load_mat
from mind_snag.types import MatchDetail, StitchResult
from mind_snag.utils.channel_info import get_np_chan_depth_info
from mind_snag.utils.psth import psth
from mind_snag.utils.sorting_utils import sort_spikes_by_rt
from mind_snag.utils.paths import (
    ks_output_dir, npclu_filename, rec_name_str, group_flag_str,
    sort_data_filename, raster_data_filename,
)

logger = logging.getLogger(__name__)


class NeuronStitcher:
    """Cross-recording neuron identity matching.

    Identifies the same neuron across multiple recordings by correlating
    firing rate PSTHs and waveform shapes.

    Parameters
    ----------
    cfg : pipeline configuration
    day : recording date (YYMMDD)
    recs : list of recording numbers
    tower : recording setup name
    np_num : probe number
    grouped : whether recordings are concatenated
    cluster_type : 'All', 'Good', or 'Isolated'
    """

    def __init__(
        self,
        cfg: MindSnagConfig,
        day: str,
        recs: list[str],
        tower: str,
        np_num: int,
        grouped: bool,
        cluster_type: str = "All",
    ):
        self.cfg = cfg
        self.day = day
        self.recs = recs
        self.tower = tower
        self.np_num = np_num
        self.grouped = grouped
        self.cluster_type = cluster_type

        self.data_root = cfg.data_root
        self.path_cfg = cfg.paths
        self.fr_threshold = cfg.stitching.fr_corr_threshold
        self.wf_threshold = cfg.stitching.wf_corr_threshold
        self.min_recs = cfg.stitching.min_recordings
        self.chan_range = cfg.stitching.channel_range
        self.top_k = cfg.stitching.top_k

        self.gflag = group_flag_str(grouped)
        self.rec_str = rec_name_str(recs, grouped)
        self.num_recs = len(recs)
        self.bn = (-300, 500)

        self.clu_info_per_rec: list[NDArray] = []
        self.chan_map: NDArray | None = None
        self.sp = None

    def run(self) -> StitchResult:
        """Execute the stitching algorithm.

        Returns
        -------
        StitchResult with stitch_table [N x num_recs] and enriched score matrices
        """
        self.cfg.validate()
        self._load_cluster_info()
        stitch_table, match_details, top_k_matches = self._run_stitching()

        n_neurons = stitch_table.shape[0]
        fr_scores = np.full((n_neurons, self.num_recs), np.nan)
        wf_scores = np.full((n_neurons, self.num_recs), np.nan)
        confidence = np.full((n_neurons, self.num_recs), np.nan)

        for i, row_details in enumerate(match_details):
            for j, detail in enumerate(row_details):
                if detail is not None:
                    fr_scores[i, j] = detail.fr_corr
                    wf_scores[i, j] = detail.wf_corr
                    confidence[i, j] = detail.confidence

        return StitchResult(
            stitch_table=stitch_table,
            recs=self.recs,
            day=self.day,
            tower=self.tower,
            np_num=self.np_num,
            match_details=match_details,
            top_k_matches=top_k_matches,
            fr_score_matrix=fr_scores,
            wf_score_matrix=wf_scores,
            confidence_matrix=confidence,
        )

    def _load_cluster_info(self) -> None:
        """Load cluster info and channel map for each recording."""
        logger.info("Loading cluster info for %d recordings...", self.num_recs)

        all_iso_chans: list[NDArray] = []

        for i_r, rec in enumerate(self.recs):
            np_file = npclu_filename(
                self.data_root, self.day, rec, self.tower, self.np_num,
                self.gflag, ext=".mat", path_cfg=self.path_cfg,
            )
            # Try HDF5 first
            np_h5 = np_file.with_suffix(".h5")

            if np_h5.exists():
                import h5py
                with h5py.File(np_h5, "r") as f:
                    clu_info = np.array(f["clu_info"])
                    ks_clu_info = np.array(f["ks_clu_info"])
                    iso_clu_info = np.array(f["iso_clu_info"]) if "iso_clu_info" in f else None
            elif np_file.exists():
                data = load_mat(np_file)
                clu_info = np.atleast_2d(data.get("Clu_info", np.empty((0, 2))))
                ks_clu_info = np.atleast_2d(data.get("KSclu_info", np.empty((0, 2))))
                iso_clu_info = np.atleast_2d(data["IsoClu_info"]) if "IsoClu_info" in data else None
            else:
                raise FileNotFoundError(
                    f"NPclu not found: {np_file}\nRun extract_spikes first."
                )

            # Select cluster type
            if self.cluster_type == "All":
                selected_info = clu_info
            elif self.cluster_type == "Good":
                selected_info = ks_clu_info
            elif self.cluster_type == "Isolated":
                if iso_clu_info is None:
                    raise ValueError(
                        f"IsoClu_info not found for rec {rec}. "
                        "Run extract_isolated_units first."
                    )
                selected_info = iso_clu_info
            else:
                raise ValueError(f"cluster_type must be 'All', 'Good', or 'Isolated', got '{self.cluster_type}'")

            self.clu_info_per_rec.append(selected_info)

            # Load channel map (once)
            if self.chan_map is None:
                ks_dir = ks_output_dir(
                    self.data_root, self.day, self.tower, self.np_num,
                    self.rec_str, self.cfg.ks_version,
                    path_cfg=self.path_cfg,
                )
                self.sp = load_ks_dir(ks_dir, exclude_noise=False)
                self.chan_map = self.sp.chan_map  # 0-indexed

            # Map channel indices to channel IDs
            chan_indices = selected_info[:, 1].astype(int) if len(selected_info) > 0 else np.array([], dtype=int)
            valid_mask = (chan_indices >= 0) & (chan_indices < len(self.chan_map))
            iso_chans = self.chan_map[chan_indices[valid_mask]]
            all_iso_chans.append(iso_chans)

        self.all_iso_chans = np.concatenate(all_iso_chans) if all_iso_chans else np.array([])
        self.uni_chans = np.unique(self.all_iso_chans)
        logger.info("Found %d unique channels across recordings.", len(self.uni_chans))

    def _get_cluster_ids(self, channel_id: int) -> list[NDArray]:
        """Get cluster IDs on a given channel across all recordings."""
        chan_ind = np.where(self.chan_map == channel_id)[0]
        result: list[NDArray] = []
        for i_r in range(self.num_recs):
            info = self.clu_info_per_rec[i_r]
            if len(info) == 0 or len(chan_ind) == 0:
                result.append(np.array([], dtype=np.int64))
                continue
            ch_match = np.isin(info[:, 1], chan_ind)
            result.append(info[ch_match, 0])
        return result

    def _get_within_range_channels(self, selected_channel: int) -> list[int]:
        """Get channel IDs within +-channel_range of selected_channel."""
        np_elec = get_np_chan_depth_info(
            self.day, self.recs[0], self.np_num, self.tower, self.data_root,
        )
        if len(np_elec.elec_num) == 0 or selected_channel >= len(np_elec.elec_num):
            return [selected_channel]

        corr_elec = np_elec.elec_num[selected_channel] if selected_channel < len(np_elec.elec_num) else 0
        elec_range = np.arange(
            corr_elec - self.chan_range,
            corr_elec + self.chan_range + 1,
        )
        chan_indices = np.where(np.isin(np_elec.elec_num, elec_range))[0]
        return chan_indices.tolist()

    def _get_waveform(self, clu: int, rec: str) -> NDArray:
        """Get waveform for a cluster from SortData."""
        sort_file = sort_data_filename(
            self.data_root, self.day, rec, self.tower, self.np_num,
            int(clu), self.gflag,
            grouped_rec_name=self.rec_str if self.grouped else None,
            ks_version=self.cfg.ks_version,
            path_cfg=self.path_cfg,
        )
        # Try .mat and .h5
        for ext in (".mat", ".h5"):
            f = sort_file.with_suffix(ext)
            if f.exists():
                if ext == ".mat":
                    data = load_mat(f)
                    sd = data.get("SortData")
                    if sd is not None:
                        wf = _extract_wf(sd)
                        if wf is not None:
                            return wf
                else:
                    import h5py
                    with h5py.File(f, "r") as hf:
                        if "frame_0000" in hf and "clu_wf" in hf["frame_0000"]:
                            return np.array(hf["frame_0000"]["clu_wf"])
        return np.full(61, np.nan)

    def _get_firing_rate(self, clu: int, rec: str) -> NDArray:
        """Get firing rate (PSTH) for a cluster from RasterData."""
        raster_file = raster_data_filename(
            self.data_root, self.day, rec, self.tower, self.np_num,
            int(clu), self.gflag,
            grouped_rec_name=self.rec_str if self.grouped else None,
            ks_version=self.cfg.ks_version,
            path_cfg=self.path_cfg,
        )
        for ext in (".mat", ".h5"):
            f = raster_file.with_suffix(ext)
            if f.exists():
                if ext == ".mat":
                    data = load_mat(f)
                    rd = data.get("RasterData")
                    if rd is not None:
                        spike_clu, rt = _extract_raster(rd)
                        if spike_clu:
                            _, sorted_sp = sort_spikes_by_rt(rt, spike_clu)
                            rate, _ = psth(sorted_sp, self.bn, smoothing=10)
                            return rate
                else:
                    import h5py
                    with h5py.File(f, "r") as hf:
                        if "spike_clu" in hf:
                            grp = hf["spike_clu"]
                            spike_clu = [np.array(grp[k]) for k in sorted(grp.keys())]
                            rt = np.array(hf["rt"]) if "rt" in hf else np.array([])
                            if spike_clu:
                                _, sorted_sp = sort_spikes_by_rt(rt, spike_clu)
                                rate, _ = psth(sorted_sp, self.bn, smoothing=10)
                                return rate

        return np.full(self.bn[1] - self.bn[0] + 1, np.nan)

    def _run_stitching(self) -> tuple[NDArray, list, list]:
        """Execute the main stitching prediction loop.

        Returns
        -------
        stitch_table, match_details, top_k_matches
        """
        logger.info("Running stitching prediction...")
        prediction_list: list[NDArray] = []
        details_list: list[list[MatchDetail | None]] = []
        topk_list: list[list[list[MatchDetail]]] = []

        for current_chan in self.uni_chans:
            nearby_chans = self._get_within_range_channels(int(current_chan))

            # Gather data for all nearby channels
            all_cluster_ids: list[NDArray] = [np.array([], dtype=np.int64) for _ in range(self.num_recs)]
            all_wfs: list[list[NDArray]] = [[] for _ in range(self.num_recs)]
            all_rates: list[list[NDArray]] = [[] for _ in range(self.num_recs)]
            all_chan_indices: list[list[int]] = [[] for _ in range(self.num_recs)]

            for ch in nearby_chans:
                ch_int = int(ch)
                if ch_int >= len(self.chan_map):
                    continue
                ch_id = self.chan_map[ch_int] if ch_int < len(self.chan_map) else ch_int
                cluster_ids = self._get_cluster_ids(ch_id)

                for i_rec in range(self.num_recs):
                    for c in cluster_ids[i_rec]:
                        all_cluster_ids[i_rec] = np.append(all_cluster_ids[i_rec], c)
                        all_wfs[i_rec].append(self._get_waveform(int(c), self.recs[i_rec]))
                        all_rates[i_rec].append(self._get_firing_rate(int(c), self.recs[i_rec]))
                        all_chan_indices[i_rec].append(ch_int)

            # Compare each cluster on current channel against other recordings
            current_clu_ids = self._get_cluster_ids(int(current_chan))

            for i_rec in range(self.num_recs):
                for clu_id in current_clu_ids[i_rec]:
                    fr = self._get_firing_rate(int(clu_id), self.recs[i_rec])
                    wf = self._get_waveform(int(clu_id), self.recs[i_rec])

                    stitched = np.full(self.num_recs, np.nan)
                    stitched[i_rec] = clu_id

                    row_details: list[MatchDetail | None] = [None] * self.num_recs
                    row_details[i_rec] = MatchDetail(
                        matched_clu=int(clu_id), fr_corr=1.0, wf_corr=1.0,
                        spatial_distance=0.0, confidence=1.0,
                    )
                    row_topk: list[list[MatchDetail]] = [[] for _ in range(self.num_recs)]

                    other_recs = [r for r in range(self.num_recs) if r != i_rec]
                    source_chan_idx = int(current_chan)

                    for other_rec in other_recs:
                        other_ids = all_cluster_ids[other_rec]
                        if len(other_ids) == 0:
                            continue

                        other_wfs = all_wfs[other_rec]
                        other_rates = all_rates[other_rec]
                        other_ch_indices = all_chan_indices[other_rec]

                        # Compute correlations
                        fr_corrs = np.array([
                            _pairwise_corr(fr, r) for r in other_rates
                        ])
                        wf_corrs = np.array([
                            _pairwise_corr(wf, w) for w in other_wfs
                        ])

                        fr_corrs_clean = np.nan_to_num(fr_corrs, nan=-np.inf)
                        sorted_indices = np.argsort(-fr_corrs_clean)

                        # Build top-K candidates
                        for ki in range(min(self.top_k, len(sorted_indices))):
                            idx = sorted_indices[ki]
                            fc = float(fr_corrs[idx]) if not np.isnan(fr_corrs[idx]) else 0.0
                            wc = float(wf_corrs[idx]) if not np.isnan(wf_corrs[idx]) else 0.0
                            sdist = float(abs(source_chan_idx - other_ch_indices[idx]))
                            conf = float(np.sqrt(max(fc, 0.0) * max(wc, 0.0)))
                            row_topk[other_rec].append(MatchDetail(
                                matched_clu=int(other_ids[idx]),
                                fr_corr=fc, wf_corr=wc,
                                spatial_distance=sdist, confidence=conf,
                            ))

                        best_idx = sorted_indices[0]
                        if fr_corrs_clean[best_idx] >= self.fr_threshold and wf_corrs[best_idx] >= self.wf_threshold:
                            stitched[other_rec] = other_ids[best_idx]
                            fc = float(fr_corrs[best_idx])
                            wc = float(wf_corrs[best_idx])
                            sdist = float(abs(source_chan_idx - other_ch_indices[best_idx]))
                            conf = float(np.sqrt(max(fc, 0.0) * max(wc, 0.0)))
                            row_details[other_rec] = MatchDetail(
                                matched_clu=int(other_ids[best_idx]),
                                fr_corr=fc, wf_corr=wc,
                                spatial_distance=sdist, confidence=conf,
                            )

                    prediction_list.append(stitched)
                    details_list.append(row_details)
                    topk_list.append(row_topk)

        if not prediction_list:
            logger.info("No stitched neurons found.")
            return np.empty((0, self.num_recs)), [], []

        # Deduplicate
        stitch_array = np.vstack(prediction_list)
        dedup = stitch_array.copy()
        dedup[np.isnan(dedup)] = 0
        _, unique_idx = np.unique(dedup, axis=0, return_index=True)
        sorted_unique_idx = np.sort(unique_idx)
        unique_stitch = stitch_array[sorted_unique_idx]
        unique_details = [details_list[i] for i in sorted_unique_idx]
        unique_topk = [topk_list[i] for i in sorted_unique_idx]

        # Filter by minimum recording count
        valid_counts = np.sum(~np.isnan(unique_stitch), axis=1)
        keep_mask = valid_counts >= self.min_recs
        stitch_table = unique_stitch[keep_mask]
        final_details = [unique_details[i] for i, k in enumerate(keep_mask) if k]
        final_topk = [unique_topk[i] for i, k in enumerate(keep_mask) if k]

        logger.info(
            "Stitching complete: %d neurons found across %d recordings.",
            stitch_table.shape[0], self.num_recs,
        )
        return stitch_table, final_details, final_topk


def _pairwise_corr(a: NDArray, b: NDArray) -> float:
    """Compute Pearson correlation handling NaN pairwise."""
    a = np.asarray(a, dtype=np.float64).flatten()
    b = np.asarray(b, dtype=np.float64).flatten()
    min_len = min(len(a), len(b))
    if min_len == 0:
        return np.nan
    a, b = a[:min_len], b[:min_len]
    valid = ~(np.isnan(a) | np.isnan(b))
    if np.sum(valid) < 2:
        return np.nan
    return float(np.corrcoef(a[valid], b[valid])[0, 1])


def _extract_wf(sort_data) -> NDArray | None:
    """Extract waveform from MATLAB SortData struct."""
    if isinstance(sort_data, dict):
        return np.atleast_1d(sort_data.get("CluWf", None))
    if isinstance(sort_data, np.ndarray) and sort_data.size > 0:
        first = sort_data.flat[0]
        if hasattr(first, "CluWf"):
            return np.atleast_1d(first.CluWf)
        if isinstance(first, dict):
            return np.atleast_1d(first.get("CluWf"))
    if hasattr(sort_data, "CluWf"):
        return np.atleast_1d(sort_data.CluWf)
    return None


def _extract_raster(raster_data):
    """Extract spike_clu and RT from MATLAB RasterData struct."""
    if isinstance(raster_data, dict):
        sc = raster_data.get("SpikeClu", [])
        rt = np.atleast_1d(raster_data.get("RT", []))
    elif hasattr(raster_data, "SpikeClu"):
        sc = raster_data.SpikeClu
        rt = np.atleast_1d(getattr(raster_data, "RT", []))
    elif isinstance(raster_data, np.ndarray) and raster_data.size > 0:
        first = raster_data.flat[0]
        if hasattr(first, "SpikeClu"):
            sc = first.SpikeClu
            rt = np.atleast_1d(getattr(first, "RT", []))
        else:
            return [], np.array([])
    else:
        return [], np.array([])

    # Convert to list
    if isinstance(sc, np.ndarray) and sc.dtype == object:
        sc = [np.atleast_1d(s) if s is not None else np.array([]) for s in sc.flat]
    elif not isinstance(sc, list):
        sc = [sc] if sc is not None else []
    return sc, rt
