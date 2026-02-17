"""Configuration dataclasses and YAML serialization.

Ports mind_snag_config.m to Python nested dataclasses with YAML support.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, asdict
from pathlib import Path
from typing import Any

import yaml


@dataclass
class CurationConfig:
    """Thresholds for auto-curation."""

    l_ratio_threshold: float = 0.2
    isi_violation_rate: float = 0.2
    isolated_t_ratio: float = 0.6


@dataclass
class StitchingConfig:
    """Parameters for cross-recording neuron stitching."""

    fr_corr_threshold: float = 0.85
    wf_corr_threshold: float = 0.85
    min_recordings: int = 2
    channel_range: int = 10


@dataclass
class RasterConfig:
    """Parameters for raster/PSTH extraction."""

    time_window: tuple[int, int] = (-300, 500)
    smoothing: int = 10


@dataclass
class IsolationConfig:
    """Parameters for isolation scoring."""

    window_sec: int = 100


@dataclass
class MindSnagConfig:
    """Central configuration for the mind_snag pipeline.

    All pipeline functions take this config as their first argument,
    replacing the old MATLAB global variables.
    """

    data_root: Path = field(default_factory=lambda: Path())
    output_root: Path | None = None
    gpu: int = 0  # 0-indexed (MATLAB was 1-indexed)
    n_threads: int = 64
    ks_version: int = 4

    curation: CurationConfig = field(default_factory=CurationConfig)
    stitching: StitchingConfig = field(default_factory=StitchingConfig)
    raster: RasterConfig = field(default_factory=RasterConfig)
    isolation: IsolationConfig = field(default_factory=IsolationConfig)

    def __post_init__(self) -> None:
        self.data_root = Path(self.data_root)
        if self.output_root is None:
            self.output_root = self.data_root
        else:
            self.output_root = Path(self.output_root)
        # Convert nested dicts from YAML loading to dataclass instances
        if isinstance(self.curation, dict):
            self.curation = CurationConfig(**self.curation)
        if isinstance(self.stitching, dict):
            self.stitching = StitchingConfig(**self.stitching)
        if isinstance(self.raster, dict):
            raster_dict = dict(self.raster)
            if "time_window" in raster_dict:
                raster_dict["time_window"] = tuple(raster_dict["time_window"])
            self.raster = RasterConfig(**raster_dict)
        if isinstance(self.isolation, dict):
            self.isolation = IsolationConfig(**self.isolation)

    @classmethod
    def from_yaml(cls, path: str | Path) -> MindSnagConfig:
        """Load configuration from a YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def to_yaml(self, path: str | Path) -> None:
        """Save configuration to a YAML file."""
        d = _config_to_dict(self)
        with open(path, "w") as f:
            yaml.dump(d, f, default_flow_style=False, sort_keys=False)

    def validate(self) -> None:
        """Validate that required paths exist."""
        if not self.data_root or not self.data_root.exists():
            raise FileNotFoundError(
                f"data_root not found: {self.data_root}. "
                "Set data_root to a valid directory."
            )


def _config_to_dict(obj: Any) -> Any:
    """Recursively convert config dataclasses to dicts for YAML."""
    if hasattr(obj, "__dataclass_fields__"):
        result = {}
        for f in fields(obj):
            val = getattr(obj, f.name)
            result[f.name] = _config_to_dict(val)
        return result
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, tuple):
        return list(obj)
    return obj
