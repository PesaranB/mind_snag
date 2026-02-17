# stitching/

Cross-recording neuron identity matching. Tracks the same neuron across multiple recordings by correlating firing rate PSTHs and waveform shapes.

## Files

- **`stitch_neurons.m`** — Core algorithm. For each unique channel across recordings, finds clusters within `cfg.stitching.channel_range` electrodes, computes pairwise Pearson correlation of PSTH and waveform across recordings, and stitches clusters that exceed both `fr_corr_threshold` and `wf_corr_threshold`. Returns an `[N x numRecs]` stitch table where each row is a neuron and each column is a recording (NaN = not found).

- **`save_stitch_results.m`** — Saves stitching results in the `NPSpike_KS4_Database` format: a `.m` script file that populates a `Session` cell array with one entry per stitched neuron, including day, recordings, tower, probe, channels, and cluster IDs.

## Algorithm Detail

1. Load cluster info (`NPclu.mat`) for each recording
2. For each unique channel, get all clusters within ±`channel_range` electrodes using `getNP_chanDepthInfo`
3. For each cluster, load its waveform (`SortData.mat`) and PSTH (`RasterData.mat`)
4. Compute Pearson correlation of PSTH and waveform against all nearby-channel clusters in other recordings
5. If best FR correlation ≥ threshold AND corresponding waveform correlation ≥ threshold → stitch
6. Deduplicate (same neuron may be found from multiple starting points) and filter by `min_recordings`

## Configuration

All thresholds come from `cfg.stitching.*`:
- `fr_corr_threshold` (default 0.85) — minimum PSTH Pearson correlation
- `wf_corr_threshold` (default 0.85) — minimum waveform Pearson correlation
- `min_recordings` (default 2) — neuron must appear in at least this many recordings
- `channel_range` (default 10) — electrode neighborhood radius for candidate matching

## Prerequisites

Requires stages 1-4 (and ideally stage 6) to have been run for each recording, so that `NPclu.mat`, `SortData.mat`, and `RasterData.mat` exist.
