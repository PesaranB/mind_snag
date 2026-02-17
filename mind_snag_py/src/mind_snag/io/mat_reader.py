"""Read .mat files (v7 and v7.3/HDF5 format).

Auto-detects format and uses scipy.io.loadmat for v7,
h5py for v7.3 (HDF5-based).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


def load_mat(path: str | Path, variable: str | None = None) -> dict[str, Any]:
    """Load a .mat file, auto-detecting v7 vs v7.3.

    Parameters
    ----------
    path : path to .mat file
    variable : if specified, load only this variable

    Returns
    -------
    dict mapping variable names to values (numpy arrays or nested dicts)
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"MAT file not found: {path}")

    if _is_hdf5(path):
        return _load_mat_v73(path, variable)
    else:
        return _load_mat_v7(path, variable)


def _is_hdf5(path: Path) -> bool:
    """Check if file starts with HDF5 magic bytes."""
    with open(path, "rb") as f:
        return f.read(4) == b"\x89HDF"


def _load_mat_v7(path: Path, variable: str | None) -> dict[str, Any]:
    """Load MAT v5/v7 file via scipy."""
    import scipy.io

    kwargs: dict[str, Any] = {"squeeze_me": True, "struct_as_record": False}
    if variable:
        kwargs["variable_names"] = [variable]
    data = scipy.io.loadmat(str(path), **kwargs)
    # Filter out metadata keys
    return {k: v for k, v in data.items() if not k.startswith("__")}


def _load_mat_v73(path: Path, variable: str | None) -> dict[str, Any]:
    """Load MAT v7.3 (HDF5) file via h5py."""
    import h5py

    result: dict[str, Any] = {}
    with h5py.File(path, "r") as f:
        keys = [variable] if variable and variable in f else list(f.keys())
        # Skip '#refs#' and other HDF5 metadata groups
        keys = [k for k in keys if not k.startswith("#")]
        for key in keys:
            result[key] = _h5_to_numpy(f[key], f)
    return result


def _h5_to_numpy(item: Any, root_file: Any) -> Any:
    """Recursively convert HDF5 items to numpy arrays or dicts."""
    import h5py

    if isinstance(item, h5py.Dataset):
        data = item[()]
        # MATLAB stores strings as uint16 arrays in v7.3
        if data.dtype == np.uint16 or (hasattr(data, 'dtype') and data.dtype.kind == 'O'):
            try:
                if isinstance(data, bytes):
                    return data.decode("utf-8")
                if isinstance(data, np.ndarray) and data.dtype == np.uint16:
                    return "".join(chr(c) for c in data.flatten())
            except (UnicodeDecodeError, TypeError):
                pass
        # MATLAB uses column-major (Fortran) order; transpose 2D arrays
        if isinstance(data, np.ndarray) and data.ndim == 2:
            data = data.T
        return data
    elif isinstance(item, h5py.Group):
        # Check if it's a MATLAB struct
        result = {}
        for key in item.keys():
            result[key] = _h5_to_numpy(item[key], root_file)
        return result
    else:
        return item
