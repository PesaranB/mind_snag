"""Experiment metadata loading utilities.

Consolidates loadExperiment.m, dayrecs.m, getRec.m, findSys.m into one module.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from mind_snag.io.mat_reader import load_mat


def load_experiment(day: str, rec: str, data_root: Path) -> dict[str, Any] | None:
    """Load experiment definition from .experiment.mat.

    Ports loadExperiment.m.

    Parameters
    ----------
    day : recording date (YYMMDD string)
    rec : recording number
    data_root : root data directory

    Returns
    -------
    experiment dict, or None if file not found
    """
    exp_file = data_root / day / rec / f"rec{rec}.experiment.mat"
    if not exp_file.exists():
        return None
    data = load_mat(exp_file, variable="experiment")
    return data.get("experiment")


def dayrecs(day: str, data_root: Path) -> list[str]:
    """List all recording directories for a given day.

    Ports dayrecs.m. Looks for numeric subdirectories under {data_root}/{day}/.

    Parameters
    ----------
    day : recording date (YYMMDD string)
    data_root : root data directory

    Returns
    -------
    Sorted list of recording directory names (e.g. ['007', '009', '010'])
    """
    day_dir = data_root / day
    if not day_dir.is_dir():
        return []

    recs = []
    for item in day_dir.iterdir():
        if item.is_dir() and re.match(r"^\d", item.name):
            recs.append(item.name)
    return sorted(recs)


def get_rec(trials: list[dict[str, Any]]) -> list[str]:
    """Extract recording identifiers from a list of trial dicts.

    Ports getRec.m.
    """
    return [t.get("Rec", "") for t in trials]


def find_sys(trials: list[dict[str, Any]], sys_name: str) -> list[int]:
    """Find which system index corresponds to a system name.

    Ports findSys.m. Returns a list of system indices (0 if no match)
    for each trial.

    Parameters
    ----------
    trials : list of trial dicts
    sys_name : system/tower name to match

    Returns
    -------
    List of system indices (one per trial, 0-indexed, 0 = no match)
    """
    pattern = re.compile(f"^{re.escape(sys_name)}")
    result = []

    for trial in trials:
        found = 0
        mt = trial.get("MT")
        if isinstance(mt, list):
            for i, name in enumerate(mt):
                if isinstance(name, str) and pattern.match(name):
                    found = i + 1
                    break
        elif isinstance(mt, str):
            if pattern.match(mt):
                found = 1
        else:
            # Legacy MT1/MT2 fields
            mt1 = trial.get("MT1", "")
            if isinstance(mt1, str) and pattern.match(mt1):
                found = 1
            else:
                mt2 = trial.get("MT2", "")
                if isinstance(mt2, str) and pattern.match(mt2):
                    found = 2
        result.append(found)

    return result
