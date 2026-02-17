"""Pipeline orchestrator for the 7 spike sorting stages.

Ports pipeline_KS4.m. Uses a Stage enum set for selective stage execution.
"""

from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path

from mind_snag.config import MindSnagConfig

logger = logging.getLogger(__name__)


class Stage(str, Enum):
    """Pipeline stages."""

    KILOSORT = "kilosort"
    EXTRACT = "extract"
    ISOLATION = "isolation"
    RASTERS = "rasters"
    CURATION = "curation"
    ISO_UNITS = "iso_units"
    HEATMAP = "heatmap"


ALL_STAGES = list(Stage)


class Pipeline:
    """Orchestrates the full spike sorting pipeline.

    Parameters
    ----------
    cfg : MindSnagConfig instance
    """

    def __init__(self, cfg: MindSnagConfig):
        self.cfg = cfg

    def run(
        self,
        day: str,
        recs: list[str],
        tower: str,
        np_num: int,
        stages: list[str | Stage] | None = None,
    ) -> None:
        """Run the pipeline.

        Parameters
        ----------
        day : recording date (YYMMDD)
        recs : list of recording numbers
        tower : recording setup name
        np_num : probe number
        stages : optional list of stage names to run (default: all)
        """
        self.cfg.validate()

        if stages is None:
            active_stages = set(ALL_STAGES)
        else:
            active_stages = {Stage(s) if isinstance(s, str) else s for s in stages}

        grouped = len(recs) > 1

        logger.info("")
        logger.info("=== mind_snag Pipeline KS4 ===")
        logger.info("Day: %s | Tower: %s | NP: %d | Grouped: %s", day, tower, np_num, grouped)
        logger.info("Recordings: %s", ", ".join(recs))
        logger.info("Stages: %s", " -> ".join(s.value for s in ALL_STAGES if s in active_stages))
        logger.info("Data root: %s", self.cfg.data_root)
        logger.info("")

        # Stage 1: Kilosort4
        if Stage.KILOSORT in active_stages:
            logger.info("--- Stage 1: Running Kilosort4 ---")
            from mind_snag.sorting.run_kilosort4 import run_kilosort4
            run_kilosort4(self.cfg, day, recs, tower, np_num, grouped)
            logger.info("--- Kilosort4 complete ---")

        # Stage 2: Spike extraction
        if Stage.EXTRACT in active_stages:
            logger.info("--- Stage 2: Extracting spikes ---")
            from mind_snag.sorting.extract_spikes import extract_spikes
            if grouped:
                extract_spikes(self.cfg, day, recs, tower, np_num, True)
            else:
                for rec in recs:
                    extract_spikes(self.cfg, day, [rec], tower, np_num, False)
            logger.info("--- Spike extraction complete ---")

        # Stage 3: Isolation analysis
        if Stage.ISOLATION in active_stages:
            logger.info("--- Stage 3: Computing isolation scores ---")
            from mind_snag.curation.compute_isolation import compute_isolation
            if grouped:
                compute_isolation(self.cfg, day, recs, tower, np_num, True)
            else:
                for rec in recs:
                    compute_isolation(self.cfg, day, [rec], tower, np_num, False)
            logger.info("--- Isolation analysis complete ---")

        # Stage 4: Raster extraction
        if Stage.RASTERS in active_stages:
            logger.info("--- Stage 4: Extracting rasters ---")
            from mind_snag.analysis.extract_rasters import extract_rasters
            if grouped:
                extract_rasters(self.cfg, day, recs, tower, np_num, True)
            else:
                for rec in recs:
                    extract_rasters(self.cfg, day, [rec], tower, np_num, False)
            logger.info("--- Raster extraction complete ---")

        # Stage 5: Auto-curation
        if Stage.CURATION in active_stages:
            logger.info("--- Stage 5: Auto-curation ---")
            logger.info(
                "Thresholds: L-Ratio=%.2f, ISI=%.2f, t-Ratio=%.2f",
                self.cfg.curation.l_ratio_threshold,
                self.cfg.curation.isi_violation_rate,
                self.cfg.curation.isolated_t_ratio,
            )
            logger.warning(
                "Programmatic auto-curation not yet implemented. Skipping."
            )
            logger.info("--- Auto-curation skipped ---")

        # Stage 6: Isolated unit extraction
        if Stage.ISO_UNITS in active_stages:
            logger.info("--- Stage 6: Extracting isolated units ---")
            from mind_snag.curation.extract_isolated_units import extract_isolated_units
            if grouped:
                extract_isolated_units(self.cfg, day, recs, tower, np_num, True)
            else:
                for rec in recs:
                    extract_isolated_units(self.cfg, day, [rec], tower, np_num, False)
            logger.info("--- Isolated unit extraction complete ---")

        # Stage 7: Visualization
        if Stage.HEATMAP in active_stages:
            logger.info("--- Stage 7: Generating heatmaps ---")
            from mind_snag.visualization.fr_heatmap import fr_heatmap
            fr_heatmap(self.cfg, day, tower, np_num, grouped, recs, show=False)
            logger.info("--- Heatmaps complete ---")

        logger.info("=== Pipeline complete ===")
