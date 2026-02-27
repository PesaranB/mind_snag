"""Stitching backend abstraction.

Defines a Protocol for stitching backends and provides implementations
for the native dual-evidence approach and UnitMatch.
"""

from __future__ import annotations

import logging
from typing import Protocol

from mind_snag.config import MindSnagConfig
from mind_snag.types import StitchResult

logger = logging.getLogger(__name__)


class StitchBackend(Protocol):
    """Protocol for stitching backends."""

    def run(
        self,
        cfg: MindSnagConfig,
        day: str,
        recs: list[str],
        tower: str,
        np_num: int,
        grouped: bool,
        cluster_type: str,
    ) -> StitchResult: ...


class NativeBackend:
    """mind_snag's dual-evidence (FR + WF correlation) stitching."""

    def run(
        self,
        cfg: MindSnagConfig,
        day: str,
        recs: list[str],
        tower: str,
        np_num: int,
        grouped: bool,
        cluster_type: str = "All",
    ) -> StitchResult:
        from mind_snag.stitching.stitch_neurons import NeuronStitcher

        stitcher = NeuronStitcher(
            cfg, day, recs, tower, np_num, grouped, cluster_type,
        )
        return stitcher.run()


class UnitMatchBackend:
    """UnitMatch waveform-only stitching via UnitMatchPy."""

    def run(
        self,
        cfg: MindSnagConfig,
        day: str,
        recs: list[str],
        tower: str,
        np_num: int,
        grouped: bool,
        cluster_type: str = "All",
    ) -> StitchResult:
        from mind_snag.stitching.unitmatch_adapter import run_unitmatch

        return run_unitmatch(
            cfg, day, recs, tower, np_num, grouped, cluster_type,
        )


_BACKENDS: dict[str, type[StitchBackend]] = {
    "native": NativeBackend,
    "unitmatch": UnitMatchBackend,
}


def get_backend(name: str) -> StitchBackend:
    """Get a stitching backend by name.

    Parameters
    ----------
    name : 'native' or 'unitmatch'

    Returns
    -------
    StitchBackend instance
    """
    cls = _BACKENDS.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown stitching backend: {name!r}. "
            f"Available: {list(_BACKENDS.keys())}"
        )
    return cls()
