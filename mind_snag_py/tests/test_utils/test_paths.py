"""Tests for path utilities."""

from pathlib import Path
from mind_snag.utils.paths import (
    group_rec_dir, ks_output_dir, npclu_filename,
    sort_data_filename, rec_name_str, group_flag_str,
)


def test_group_rec_dir():
    p = group_rec_dir(Path("/data"), "250224", "LPPC", 1)
    assert p == Path("/data/250224/spikeglx_data/grouped_recordings.LPPC.1")


def test_ks_output_dir():
    p = ks_output_dir(Path("/data"), "250224", "LPPC", 1, "007_009", ks_version=4)
    assert p == Path("/data/250224/spikeglx_data/grouped_recordings.LPPC.1/group007_009_KS4")


def test_npclu_filename():
    p = npclu_filename(Path("/data"), "250224", "007", "LPPC", 1, "Grouped")
    assert p == Path("/data/250224/007/rec007.LPPC.1.Grouped.NPclu.mat")


def test_sort_data_filename_grouped():
    p = sort_data_filename(
        Path("/data"), "250224", "007", "LPPC", 1, 42, "Grouped",
        grouped_rec_name="007_009",
    )
    assert "007_009" in str(p)
    assert "KSsave_KS4" in str(p)


def test_rec_name_str():
    assert rec_name_str(["007", "009"], grouped=True) == "007_009"
    assert rec_name_str(["007"], grouped=False) == "007"


def test_group_flag_str():
    assert group_flag_str(True) == "Grouped"
    assert group_flag_str(False) == "NotGrouped"
