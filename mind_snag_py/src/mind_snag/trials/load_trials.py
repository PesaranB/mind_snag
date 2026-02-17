"""Load behavioral trial data.

Ports loadTrials.m.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

from mind_snag.io.mat_reader import load_mat

logger = logging.getLogger(__name__)


def load_trials(
    day: str,
    rec: str | list[str] | None,
    data_root: Path,
) -> list[dict[str, Any]]:
    """Load behavioral trial data for a recording day.

    Parameters
    ----------
    day : recording date (YYMMDD string)
    rec : recording number(s) to filter, or None for all
    data_root : root data directory

    Returns
    -------
    list of trial dicts
    """
    tr_file = data_root / day / "mat" / "Trials.mat"
    if not tr_file.exists():
        logger.warning("No Trials data found: %s", tr_file)
        return []

    data = load_mat(tr_file)
    trials_raw = data.get("Trials")

    if trials_raw is None:
        return []

    # Convert from scipy struct array to list of dicts
    trials = _struct_to_dicts(trials_raw)

    # Filter by recording
    if rec is not None and len(trials) > 0:
        if isinstance(rec, str):
            rec = [rec]
        trials = [t for t in trials if t.get("Rec", "") in rec]

    return trials


def _struct_to_dicts(struct_array: Any) -> list[dict[str, Any]]:
    """Convert a MATLAB struct array to a list of Python dicts."""
    if isinstance(struct_array, list):
        return [_single_struct_to_dict(s) for s in struct_array]
    if isinstance(struct_array, dict):
        return [struct_array]
    if isinstance(struct_array, np.ndarray):
        if struct_array.dtype.names is not None:
            # Structured array
            result = []
            for i in range(len(struct_array)):
                d = {}
                for name in struct_array.dtype.names:
                    val = struct_array[name][i]
                    d[name] = _unwrap_scalar(val)
                result.append(d)
            return result
        elif hasattr(struct_array, '__iter__'):
            return [_single_struct_to_dict(s) for s in struct_array.flat]
    # scipy mat_struct objects
    if hasattr(struct_array, '_fieldnames'):
        n = 1
        first_field = getattr(struct_array, struct_array._fieldnames[0], None)
        if isinstance(first_field, np.ndarray) and first_field.ndim > 0:
            n = len(first_field)
        if n == 1:
            return [_single_struct_to_dict(struct_array)]
        result = []
        for i in range(n):
            d = {}
            for name in struct_array._fieldnames:
                val = getattr(struct_array, name)
                if isinstance(val, np.ndarray) and len(val) > i:
                    d[name] = _unwrap_scalar(val[i])
                else:
                    d[name] = _unwrap_scalar(val)
            result.append(d)
        return result
    return []


def _single_struct_to_dict(s: Any) -> dict[str, Any]:
    """Convert a single MATLAB struct to a dict."""
    if isinstance(s, dict):
        return s
    if hasattr(s, '_fieldnames'):
        return {name: _unwrap_scalar(getattr(s, name)) for name in s._fieldnames}
    return {}


def _unwrap_scalar(val: Any) -> Any:
    """Unwrap numpy scalars and single-element arrays."""
    if isinstance(val, np.ndarray):
        if val.size == 1:
            return val.item()
        if val.dtype.kind in ('U', 'S', 'O') and val.size == 1:
            return str(val.item())
    return val
