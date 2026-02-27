"""Path convention helpers for the mind_snag data layout.

Centralizes the path patterns used throughout the pipeline so that
individual modules don't hardcode path construction.
"""

from __future__ import annotations

from pathlib import Path

from mind_snag.config import PathConfig


def resolve_path(
    data_root: Path,
    template: str,
    variables: dict,
    ext: str = "",
) -> Path:
    """Resolve a path template with the given variables.

    Parameters
    ----------
    data_root : root data directory
    template : path template string with {variable} placeholders
    variables : dict mapping placeholder names to values
    ext : optional file extension to append (e.g. ".h5")

    Returns
    -------
    Fully resolved Path
    """
    resolved = template.format_map(variables)
    return data_root / (resolved + ext)


def build_variables(
    day: str,
    rec: str,
    tower: str,
    np_num: int,
    group_flag: str,
    rec_name: str,
    ks_version: int = 4,
    clu: int | None = None,
    grouped_rec_name: str | None = None,
) -> dict:
    """Build the standard variable dict for path template substitution."""
    ks_save_prefix = f"KSsave_KS{ks_version}/" if ks_version else ""
    if grouped_rec_name:
        ks_save_prefix = f"{grouped_rec_name}/{ks_save_prefix}"

    variables = {
        "day": day,
        "rec": rec,
        "tower": tower,
        "np_num": np_num,
        "group_flag": group_flag,
        "rec_name": rec_name,
        "ks_save_prefix": ks_save_prefix,
    }
    if clu is not None:
        variables["clu"] = clu
    return variables


# --- Convenience wrappers (backward compatible) ---


def group_rec_dir(data_root: Path, day: str, tower: str, np_num: int,
                  path_cfg: PathConfig | None = None) -> Path:
    """Directory containing grouped recording KS output."""
    if path_cfg is not None:
        variables = {"day": day, "tower": tower, "np_num": np_num}
        return resolve_path(data_root, path_cfg.group_rec, variables)
    return data_root / day / "spikeglx_data" / f"grouped_recordings.{tower}.{np_num}"


def ks_output_dir(
    data_root: Path, day: str, tower: str, np_num: int,
    rec_name: str, ks_version: int = 4,
    path_cfg: PathConfig | None = None,
) -> Path:
    """Kilosort output directory for a specific recording group."""
    if path_cfg is not None:
        variables = {
            "day": day, "tower": tower, "np_num": np_num,
            "rec_name": rec_name,
        }
        return resolve_path(data_root, path_cfg.ks_output, variables)
    suffix = "_KS4" if ks_version == 4 else ""
    return group_rec_dir(data_root, day, tower, np_num) / f"group{rec_name}{suffix}"


def npclu_filename(
    data_root: Path, day: str, rec: str, tower: str,
    np_num: int, group_flag: str, ext: str = ".mat",
    path_cfg: PathConfig | None = None,
) -> Path:
    """NPclu output file path."""
    if path_cfg is not None:
        variables = {
            "day": day, "rec": rec, "tower": tower,
            "np_num": np_num, "group_flag": group_flag,
        }
        return resolve_path(data_root, path_cfg.npclu, variables, ext=ext)
    name = f"rec{rec}.{tower}.{np_num}.{group_flag}.NPclu{ext}"
    return data_root / day / rec / name


def sort_data_filename(
    data_root: Path, day: str, rec: str, tower: str,
    np_num: int, clu: int, group_flag: str,
    grouped_rec_name: str | None = None,
    ks_version: int = 4, ext: str = ".mat",
    path_cfg: PathConfig | None = None,
) -> Path:
    """SortData output file path."""
    if path_cfg is not None:
        ks_save_prefix = f"KSsave_KS{ks_version}/" if ks_version else ""
        if grouped_rec_name:
            ks_save_prefix = f"{grouped_rec_name}/{ks_save_prefix}"
        variables = {
            "day": day, "rec": rec, "tower": tower,
            "np_num": np_num, "clu": clu, "group_flag": group_flag,
            "ks_save_prefix": ks_save_prefix,
        }
        return resolve_path(data_root, path_cfg.sort_data, variables, ext=ext)
    ks_save = "KSsave_KS4" if ks_version == 4 else ""
    name = f"rec{rec}.{tower}.{np_num}.{clu}.{group_flag}.SortData{ext}"
    if grouped_rec_name:
        return data_root / day / rec / grouped_rec_name / ks_save / name
    return data_root / day / rec / ks_save / name


def raster_data_filename(
    data_root: Path, day: str, rec: str, tower: str,
    np_num: int, clu: int, group_flag: str,
    grouped_rec_name: str | None = None,
    ks_version: int = 4, ext: str = ".mat",
    path_cfg: PathConfig | None = None,
) -> Path:
    """RasterData output file path."""
    if path_cfg is not None:
        ks_save_prefix = f"KSsave_KS{ks_version}/" if ks_version else ""
        if grouped_rec_name:
            ks_save_prefix = f"{grouped_rec_name}/{ks_save_prefix}"
        variables = {
            "day": day, "rec": rec, "tower": tower,
            "np_num": np_num, "clu": clu, "group_flag": group_flag,
            "ks_save_prefix": ks_save_prefix,
        }
        return resolve_path(data_root, path_cfg.raster_data, variables, ext=ext)
    ks_save = "KSsave_KS4" if ks_version == 4 else ""
    name = f"rec{rec}.{tower}.{np_num}.{clu}.{group_flag}.RasterData{ext}"
    if grouped_rec_name:
        return data_root / day / rec / grouped_rec_name / ks_save / name
    return data_root / day / rec / ks_save / name


def rec_name_str(recs: list[str], grouped: bool) -> str:
    """Build the recording name string used in file/directory names."""
    if grouped:
        return "_".join(recs)
    return recs[0]


def group_flag_str(grouped: bool) -> str:
    """Return 'Grouped' or 'NotGrouped'."""
    return "Grouped" if grouped else "NotGrouped"
