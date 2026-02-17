"""Trial-aligned Neuropixel spike extraction.

Ports trialNPSpike.m and loadnpspike.m into one module.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from mind_snag.io.mat_reader import load_mat
from mind_snag.utils.experiment import dayrecs, get_rec, load_experiment
from mind_snag.utils.paths import npclu_filename, group_flag_str

logger = logging.getLogger(__name__)

FS = 30000  # Neuropixel sampling rate


def trial_np_spike(
    trials: list[dict[str, Any]],
    tower: str,
    np_num: int,
    cluster_id: int,
    event_field: str,
    bn: tuple[int, int],
    data_root: Path,
    ks_version: int = 4,
    grouped: bool = False,
) -> list[NDArray[np.float64]]:
    """Load trial-aligned spike data for a cluster.

    Ports trialNPSpike.m. For each trial, extracts spikes within a time window
    around the specified behavioral event.

    Parameters
    ----------
    trials : list of trial dicts
    tower : system/tower name
    np_num : probe number
    cluster_id : cluster ID to extract (1-indexed, as in MATLAB NPclu)
    event_field : event name to align to (e.g. 'TargsOn')
    bn : (start, stop) time window in ms
    data_root : root data directory
    ks_version : Kilosort version (4 or 2.5)
    grouped : whether recordings are concatenated

    Returns
    -------
    list of spike time arrays (one per trial), times in ms relative to event
    """
    if not trials:
        return []

    day = trials[0].get("Day", "")
    n_total_tr = len(trials)
    spike_result: list[NDArray[np.float64]] = [np.array([]) for _ in range(n_total_tr)]

    trial_recs = get_rec(trials)
    all_recs = dayrecs(day, data_root)
    gflag = group_flag_str(grouped)

    for rec in all_recs:
        rec_trial_indices = [i for i, r in enumerate(trial_recs) if r == rec]
        if not rec_trial_indices:
            continue

        # Load Events
        events = _load_events(data_root, day, rec)
        if events is None:
            continue

        # Load NPclu
        npclu = _load_npclu(data_root, day, rec, tower, np_num, gflag, ks_version)
        if npclu is None:
            continue

        for i_tr in rec_trial_indices:
            subtrial = trials[i_tr].get("Trial", i_tr)
            spike_result[i_tr] = _load_np_spike(
                npclu, events, subtrial, event_field, bn, cluster_id,
            )

    return spike_result


def _load_events(data_root: Path, day: str, rec: str) -> dict[str, Any] | None:
    """Load behavioral events for a recording."""
    candidates = [
        (data_root / day / rec / f"rec{rec}.SequenceEvents.mat", "SequenceEvents"),
        (data_root / day / rec / f"rec{rec}.Events.mat", "Events"),
        (data_root / day / rec / f"rec{rec}.SpontEvents.mat", "SpontEvents"),
        (data_root / day / rec / f"rec{rec}.MocapEvents.mat", "MocapEvents"),
    ]
    for path, var_name in candidates:
        if path.exists():
            data = load_mat(path)
            events = data.get(var_name)
            if events is not None:
                return events if isinstance(events, dict) else {}
    return None


def _load_npclu(
    data_root: Path, day: str, rec: str, tower: str,
    np_num: int, gflag: str, ks_version: int,
) -> NDArray | None:
    """Load the NPclu matrix for a recording."""
    if ks_version == 4:
        ks_save = "KSsave_KS4"
        npclu_path = data_root / day / rec / ks_save / f"rec{rec}.{tower}.{np_num}.{gflag}.NPclu.mat"
        if not npclu_path.exists():
            npclu_path = data_root / day / rec / f"rec{rec}.{tower}.{np_num}.{gflag}.NPclu.mat"
    else:
        npclu_path = data_root / day / rec / f"rec{rec}.{tower}.{np_num}.NPclu.mat"

    if not npclu_path.exists():
        return None

    data = load_mat(npclu_path)
    return data.get("NPclu")


def _load_np_spike(
    npclu: NDArray,
    events: dict[str, Any],
    subtrial: int,
    event_field: str,
    bn: tuple[int, int],
    cluster_id: int,
) -> NDArray[np.float64]:
    """Extract spike times for a single trial and cluster relative to an event.

    Ports loadnpspike.m.

    Parameters
    ----------
    npclu : [N, 2] array of (spike_time, cluster_id)
    events : events dict with field arrays
    subtrial : trial index within this recording (0-indexed in Python)
    event_field : event name
    bn : time window in ms
    cluster_id : cluster ID (1-indexed, matching NPclu column 2)

    Returns
    -------
    spike times in ms relative to event
    """
    if npclu is None or len(npclu) == 0:
        return np.array([], dtype=np.float64)

    # Get event time
    event_times = events.get(event_field)
    if event_times is None:
        return np.array([], dtype=np.float64)

    event_times = np.atleast_1d(event_times)
    # subtrial is typically 1-indexed from MATLAB Trials struct
    idx = int(subtrial) - 1 if int(subtrial) > 0 else 0
    if idx >= len(event_times):
        return np.array([], dtype=np.float64)

    event_time = float(event_times[idx])
    if np.isnan(event_time) or event_time == 0:
        return np.array([], dtype=np.float64)

    # Convert event time to samples
    event_sample = event_time * FS / 1000.0

    # Find spikes for this cluster
    npclu = np.asarray(npclu)
    clu_mask = npclu[:, 1] == cluster_id
    clu_spikes = npclu[clu_mask, 0]

    # Find spikes in window
    start_sample = event_sample + bn[0] * FS / 1000.0
    end_sample = event_sample + bn[1] * FS / 1000.0
    window_mask = (clu_spikes >= start_sample) & (clu_spikes <= end_sample)
    window_spikes = clu_spikes[window_mask]

    # Convert to ms relative to event
    spike_times = (window_spikes - event_sample) * 1000.0 / FS
    return spike_times
