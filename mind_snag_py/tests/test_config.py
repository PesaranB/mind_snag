"""Tests for config module."""

from pathlib import Path

import pytest
import yaml

from mind_snag.config import MindSnagConfig, CurationConfig, StitchingConfig


class TestMindSnagConfig:
    def test_defaults(self):
        cfg = MindSnagConfig()
        assert cfg.gpu == 0
        assert cfg.ks_version == 4
        assert cfg.curation.l_ratio_threshold == 0.2
        assert cfg.stitching.fr_corr_threshold == 0.85
        assert cfg.raster.time_window == (-300, 500)
        assert cfg.isolation.window_sec == 100

    def test_output_root_defaults_to_data_root(self, tmp_path):
        cfg = MindSnagConfig(data_root=tmp_path)
        assert cfg.output_root == tmp_path

    def test_explicit_output_root(self, tmp_path):
        out = tmp_path / "output"
        cfg = MindSnagConfig(data_root=tmp_path, output_root=out)
        assert cfg.output_root == out

    def test_from_yaml(self, tmp_path):
        config = {
            "data_root": str(tmp_path),
            "gpu": 1,
            "stitching": {
                "fr_corr_threshold": 0.5,
                "wf_corr_threshold": 0.6,
            },
        }
        yaml_path = tmp_path / "config.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(config, f)

        cfg = MindSnagConfig.from_yaml(yaml_path)
        assert cfg.data_root == tmp_path
        assert cfg.gpu == 1
        assert cfg.stitching.fr_corr_threshold == 0.5
        assert cfg.stitching.wf_corr_threshold == 0.6

    def test_to_yaml(self, tmp_path):
        cfg = MindSnagConfig(data_root=tmp_path)
        yaml_path = tmp_path / "out.yaml"
        cfg.to_yaml(yaml_path)

        loaded = MindSnagConfig.from_yaml(yaml_path)
        assert loaded.data_root == tmp_path
        assert loaded.curation.l_ratio_threshold == cfg.curation.l_ratio_threshold

    def test_validate_missing_data_root(self):
        cfg = MindSnagConfig(data_root="/nonexistent/path/abc123")
        with pytest.raises(FileNotFoundError):
            cfg.validate()

    def test_validate_existing_data_root(self, tmp_path):
        cfg = MindSnagConfig(data_root=tmp_path)
        cfg.validate()  # should not raise

    def test_nested_dict_conversion(self, tmp_path):
        """Config should handle dicts passed for nested fields (e.g. from YAML)."""
        cfg = MindSnagConfig(
            data_root=tmp_path,
            curation={"l_ratio_threshold": 0.5, "isi_violation_rate": 0.1, "isolated_t_ratio": 0.8},
        )
        assert isinstance(cfg.curation, CurationConfig)
        assert cfg.curation.l_ratio_threshold == 0.5
