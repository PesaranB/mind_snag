"""Peri-stimulus time histogram with Gaussian smoothing.

Ports psth.m. Computes firing rate from trial-aligned spike times.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.stats import norm


def psth(
    spike_cell: list[NDArray[np.float64]],
    bn: tuple[int, int],
    smoothing: float = 50.0,
    max_rate: float = 50.0,
) -> tuple[NDArray[np.float64], int]:
    """Compute PSTH from a list of per-trial spike times.

    Parameters
    ----------
    spike_cell : list of arrays, each containing spike times in ms
    bn : (start, stop) time window in ms
    smoothing : Gaussian smoothing std in ms
    max_rate : not used in computation, kept for API compat

    Returns
    -------
    rate : smoothed firing rate vector (spikes/s), length = stop - start + 1
    n_tr : number of trials
    """
    n_tr = len(spike_cell)
    if n_tr == 0:
        return np.zeros(bn[1] - bn[0] + 1), 0

    start, stop = bn
    time_bins = np.arange(start, stop + 1, dtype=np.float64)

    # Collect all spikes shifted by start
    all_spikes = []
    for spikes in spike_cell:
        if spikes is not None and len(spikes) > 0:
            arr = np.asarray(spikes).flatten()
            all_spikes.append(arr)
    if all_spikes:
        xx = np.concatenate(all_spikes)
    else:
        xx = np.array([])

    # Histogram
    z, _ = np.histogram(xx, bins=len(time_bins), range=(start, stop))
    z = z.astype(np.float64)

    # Gaussian smoothing kernel
    half_width = int(3 * smoothing)
    kernel_x = np.arange(-half_width, half_width + 1, dtype=np.float64)
    window = norm.pdf(kernel_x, 0, smoothing)

    # Convolve and trim
    rate = (1000.0 / n_tr) * np.convolve(z, window)
    rate = rate[half_width: half_width + len(time_bins)]

    return rate, n_tr
