"""Tests for enriched stitch output (Phase 2)."""

from pathlib import Path

import h5py
import numpy as np
import pytest

from mind_snag.types import MatchDetail, StitchResult


class TestMatchDetail:
    def test_creation(self):
        md = MatchDetail(
            matched_clu=42, fr_corr=0.95, wf_corr=0.88,
            spatial_distance=2.0, confidence=0.914,
        )
        assert md.matched_clu == 42
        assert md.fr_corr == 0.95
        assert md.wf_corr == 0.88
        assert md.spatial_distance == 2.0
        assert abs(md.confidence - 0.914) < 0.01

    def test_confidence_formula(self):
        """Confidence = sqrt(fr_corr * wf_corr)."""
        fr, wf = 0.9, 0.81
        expected = float(np.sqrt(fr * wf))
        md = MatchDetail(
            matched_clu=1, fr_corr=fr, wf_corr=wf,
            spatial_distance=0, confidence=expected,
        )
        assert abs(md.confidence - expected) < 1e-6


class TestEnrichedStitchResult:
    def test_backward_compat(self):
        """StitchResult still works with just stitch_table."""
        table = np.array([[1, 2], [3, np.nan]])
        result = StitchResult(stitch_table=table, recs=["007", "009"])
        assert result.stitch_table.shape == (2, 2)
        assert result.match_details is None
        assert result.fr_score_matrix is None

    def test_enriched_fields(self):
        table = np.array([[1, 2], [3, np.nan]])
        fr_scores = np.array([[1.0, 0.92], [1.0, np.nan]])
        wf_scores = np.array([[1.0, 0.88], [1.0, np.nan]])
        confidence = np.sqrt(np.maximum(fr_scores, 0) * np.maximum(wf_scores, 0))

        md = MatchDetail(matched_clu=2, fr_corr=0.92, wf_corr=0.88,
                         spatial_distance=1.0, confidence=float(np.sqrt(0.92 * 0.88)))
        details = [
            [MatchDetail(matched_clu=1, fr_corr=1.0, wf_corr=1.0,
                         spatial_distance=0.0, confidence=1.0), md],
            [MatchDetail(matched_clu=3, fr_corr=1.0, wf_corr=1.0,
                         spatial_distance=0.0, confidence=1.0), None],
        ]

        result = StitchResult(
            stitch_table=table, recs=["007", "009"],
            match_details=details,
            fr_score_matrix=fr_scores,
            wf_score_matrix=wf_scores,
            confidence_matrix=confidence,
        )
        assert result.fr_score_matrix[0, 1] == 0.92
        assert result.wf_score_matrix[0, 1] == 0.88
        assert result.match_details[0][1].matched_clu == 2

    def test_sessions_field(self):
        result = StitchResult(
            stitch_table=np.empty((0, 2)),
            sessions=[{"day": "250224", "rec": "007"}, {"day": "250224", "rec": "009"}],
            recs=["007", "009"],
        )
        assert len(result.sessions) == 2
        assert result.sessions[0]["rec"] == "007"


class TestSaveEnrichedHDF5:
    def test_save_loads_scores(self, tmp_path):
        from mind_snag.config import MindSnagConfig
        from mind_snag.stitching.save_stitch_results import save_stitch_results

        table = np.array([[1.0, 2.0], [3.0, np.nan]])
        fr_scores = np.array([[1.0, 0.92], [1.0, np.nan]])
        wf_scores = np.array([[1.0, 0.88], [1.0, np.nan]])
        confidence = np.array([[1.0, 0.9], [1.0, np.nan]])

        result = StitchResult(
            stitch_table=table, recs=["007", "009"],
            day="250224", tower="LPPC", np_num=1,
            fr_score_matrix=fr_scores,
            wf_score_matrix=wf_scores,
            confidence_matrix=confidence,
            top_k_matches=[
                [
                    [],  # rec 0 (self)
                    [MatchDetail(matched_clu=2, fr_corr=0.92, wf_corr=0.88,
                                 spatial_distance=1.0, confidence=0.9)],
                ],
                [
                    [],
                    [],
                ],
            ],
        )

        cfg = MindSnagConfig(data_root=tmp_path)
        out = save_stitch_results(cfg, result, tmp_path, format="hdf5")

        with h5py.File(out, "r") as f:
            assert "fr_scores" in f
            assert "wf_scores" in f
            assert "confidence" in f
            assert f["fr_scores"][0, 1] == pytest.approx(0.92)
            assert "top_k_matches" in f
            assert "neuron_0000" in f["top_k_matches"]
            assert "rec_1" in f["top_k_matches"]["neuron_0000"]
            assert f["top_k_matches"]["neuron_0000"]["rec_1"]["fr_corrs"][0] == pytest.approx(0.92)
