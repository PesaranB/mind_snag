"""Tests for configurable path templates."""

from pathlib import Path

import pytest
import yaml

from mind_snag.config import MindSnagConfig, PathConfig
from mind_snag.utils.paths import (
    resolve_path,
    build_variables,
    group_rec_dir,
    ks_output_dir,
    npclu_filename,
    sort_data_filename,
    raster_data_filename,
)


class TestResolve:
    def test_basic_substitution(self, tmp_path):
        result = resolve_path(tmp_path, "{day}/{rec}/output", {"day": "250224", "rec": "007"})
        assert result == tmp_path / "250224" / "007" / "output"

    def test_with_extension(self, tmp_path):
        result = resolve_path(tmp_path, "{day}/{rec}/file", {"day": "250224", "rec": "007"}, ext=".h5")
        assert result == tmp_path / "250224" / "007" / "file.h5"

    def test_numeric_values(self, tmp_path):
        result = resolve_path(tmp_path, "probe{np_num}", {"np_num": 1})
        assert result == tmp_path / "probe1"

    def test_missing_key_raises(self, tmp_path):
        with pytest.raises(KeyError):
            resolve_path(tmp_path, "{day}/{missing}", {"day": "250224"})


class TestBuildVariables:
    def test_basic(self):
        v = build_variables("250224", "007", "LPPC", 1, "Grouped", "007_009")
        assert v["day"] == "250224"
        assert v["rec"] == "007"
        assert v["tower"] == "LPPC"
        assert v["np_num"] == 1
        assert v["group_flag"] == "Grouped"
        assert v["rec_name"] == "007_009"
        assert v["ks_save_prefix"] == "KSsave_KS4/"

    def test_with_grouped_rec_name(self):
        v = build_variables("250224", "007", "LPPC", 1, "Grouped", "007_009",
                            grouped_rec_name="007_009")
        assert v["ks_save_prefix"] == "007_009/KSsave_KS4/"

    def test_with_clu(self):
        v = build_variables("250224", "007", "LPPC", 1, "Grouped", "007_009", clu=42)
        assert v["clu"] == 42


class TestPathConfigDefaults:
    """Verify default PathConfig produces same paths as legacy hardcoded functions."""

    def test_group_rec_dir(self, tmp_path):
        cfg = PathConfig()
        result = group_rec_dir(tmp_path, "250224", "LPPC", 1, path_cfg=cfg)
        legacy = tmp_path / "250224" / "spikeglx_data" / "grouped_recordings.LPPC.1"
        assert result == legacy

    def test_ks_output_dir(self, tmp_path):
        cfg = PathConfig()
        result = ks_output_dir(tmp_path, "250224", "LPPC", 1, "007_009", 4, path_cfg=cfg)
        legacy = tmp_path / "250224" / "spikeglx_data" / "grouped_recordings.LPPC.1" / "group007_009_KS4"
        assert result == legacy

    def test_npclu_filename(self, tmp_path):
        cfg = PathConfig()
        result = npclu_filename(tmp_path, "250224", "007", "LPPC", 1, "Grouped",
                                ext=".h5", path_cfg=cfg)
        legacy = tmp_path / "250224" / "007" / "rec007.LPPC.1.Grouped.NPclu.h5"
        assert result == legacy

    def test_sort_data_filename_nongrouped(self, tmp_path):
        cfg = PathConfig()
        result = sort_data_filename(
            tmp_path, "250224", "007", "LPPC", 1, 42, "NotGrouped",
            ks_version=4, ext=".h5", path_cfg=cfg,
        )
        legacy = sort_data_filename(
            tmp_path, "250224", "007", "LPPC", 1, 42, "NotGrouped",
            ks_version=4, ext=".h5",
        )
        assert result == legacy

    def test_sort_data_filename_grouped(self, tmp_path):
        cfg = PathConfig()
        result = sort_data_filename(
            tmp_path, "250224", "007", "LPPC", 1, 42, "Grouped",
            grouped_rec_name="007_009", ks_version=4, ext=".h5", path_cfg=cfg,
        )
        legacy = sort_data_filename(
            tmp_path, "250224", "007", "LPPC", 1, 42, "Grouped",
            grouped_rec_name="007_009", ks_version=4, ext=".h5",
        )
        assert result == legacy

    def test_raster_data_filename(self, tmp_path):
        cfg = PathConfig()
        result = raster_data_filename(
            tmp_path, "250224", "007", "LPPC", 1, 42, "Grouped",
            grouped_rec_name="007_009", ks_version=4, ext=".h5", path_cfg=cfg,
        )
        legacy = raster_data_filename(
            tmp_path, "250224", "007", "LPPC", 1, 42, "Grouped",
            grouped_rec_name="007_009", ks_version=4, ext=".h5",
        )
        assert result == legacy


class TestPathConfigFromYAML:
    def test_default_paths_in_config(self):
        cfg = MindSnagConfig()
        assert isinstance(cfg.paths, PathConfig)
        assert "{day}" in cfg.paths.raw_data

    def test_yaml_round_trip(self, tmp_path):
        cfg = MindSnagConfig(data_root=tmp_path)
        yaml_path = tmp_path / "config.yaml"
        cfg.to_yaml(yaml_path)
        loaded = MindSnagConfig.from_yaml(yaml_path)
        assert isinstance(loaded.paths, PathConfig)
        assert loaded.paths.raw_data == cfg.paths.raw_data

    def test_custom_paths_from_yaml(self, tmp_path):
        config = {
            "data_root": str(tmp_path),
            "paths": {
                "raw_data": "{subject}/{session}/raw",
                "ks_output": "{subject}/{session}/sorted",
                "npclu": "{subject}/{session}/npclu_{probe}",
                "sort_data": "{subject}/{session}/clusters/{clu}/sort",
                "raster_data": "{subject}/{session}/clusters/{clu}/raster",
            },
        }
        yaml_path = tmp_path / "custom.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(config, f)

        cfg = MindSnagConfig.from_yaml(yaml_path)
        assert cfg.paths.raw_data == "{subject}/{session}/raw"
        assert cfg.paths.ks_output == "{subject}/{session}/sorted"


class TestCustomLabLayout:
    """Verify path resolution works for a non-Pesaran lab layout."""

    def test_flat_session_layout(self, tmp_path):
        cfg = PathConfig(
            raw_data="{subject}/{session}/raw",
            ks_output="{subject}/{session}/sorted",
            npclu="{subject}/{session}/npclu_{probe}",
            sort_data="{subject}/{session}/clusters/clu{clu}_sort",
            raster_data="{subject}/{session}/clusters/clu{clu}_raster",
        )
        variables = {"subject": "monkey_A", "session": "20250224_01", "probe": "0"}
        result = resolve_path(tmp_path, cfg.npclu, variables, ext=".h5")
        assert result == tmp_path / "monkey_A" / "20250224_01" / "npclu_0.h5"

        variables["clu"] = 5
        result = resolve_path(tmp_path, cfg.sort_data, variables, ext=".h5")
        assert result == tmp_path / "monkey_A" / "20250224_01" / "clusters" / "clu5_sort.h5"

    def test_ks_output_with_custom_cfg_mismatched_vars(self, tmp_path):
        """Custom templates with non-standard variable names raise KeyError
        when called via the convenience wrappers (which pass standard vars).
        Custom labs should use resolve_path() directly instead."""
        cfg = PathConfig(
            ks_output="{subject}/{session}/kilosort",
        )
        with pytest.raises(KeyError):
            ks_output_dir(
                tmp_path, "250224", "LPPC", 1, "007", 4,
                path_cfg=cfg,
            )

    def test_custom_vars_via_resolve_path(self, tmp_path):
        """Custom labs use resolve_path() directly with their own variable dicts."""
        cfg = PathConfig(
            ks_output="{subject}/{session}/kilosort",
        )
        result = resolve_path(
            tmp_path, cfg.ks_output,
            {"subject": "monkey_A", "session": "20250224_01"},
        )
        assert result == tmp_path / "monkey_A" / "20250224_01" / "kilosort"
