"""Path convention helpers for the mind_snag data layout.

Centralizes the path patterns used throughout the pipeline so that
individual modules don't hardcode path construction.
"""

from __future__ import annotations

from pathlib import Path


def group_rec_dir(data_root: Path, day: str, tower: str, np_num: int) -> Path:
    """Directory containing grouped recording KS output.

    ``{data_root}/{day}/spikeglx_data/grouped_recordings.{tower}.{np}/``
    """
    return data_root / day / "spikeglx_data" / f"grouped_recordings.{tower}.{np_num}"


def ks_output_dir(
    data_root: Path, day: str, tower: str, np_num: int,
    rec_name: str, ks_version: int = 4,
) -> Path:
    """Kilosort output directory for a specific recording group.

    ``{group_rec_dir}/group{rec_name}_KS4/``
    """
    suffix = "_KS4" if ks_version == 4 else ""
    return group_rec_dir(data_root, day, tower, np_num) / f"group{rec_name}{suffix}"


def npclu_filename(
    data_root: Path, day: str, rec: str, tower: str,
    np_num: int, group_flag: str, ext: str = ".mat",
) -> Path:
    """NPclu output file path.

    ``{data_root}/{day}/{rec}/rec{rec}.{tower}.{np}.{GroupFlag}.NPclu.{ext}``
    """
    name = f"rec{rec}.{tower}.{np_num}.{group_flag}.NPclu{ext}"
    return data_root / day / rec / name


def sort_data_filename(
    data_root: Path, day: str, rec: str, tower: str,
    np_num: int, clu: int, group_flag: str,
    grouped_rec_name: str | None = None,
    ks_version: int = 4, ext: str = ".mat",
) -> Path:
    """SortData output file path.

    Grouped: ``{data_root}/{day}/{rec}/{grouped_rec_name}/KSsave_KS4/rec{rec}...``
    Non-grouped: ``{data_root}/{day}/{rec}/KSsave_KS4/rec{rec}...``
    """
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
) -> Path:
    """RasterData output file path."""
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
