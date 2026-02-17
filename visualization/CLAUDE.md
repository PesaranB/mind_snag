# visualization/

Plotting functions for spike sorting results.

## Files

- **`fr_heatmap.m`** — Generates depth-sorted firing rate heatmaps. For each recording, loads all clusters' `RasterData.mat` files, computes PSTHs via `psth()`, sorts them by probe depth (using `getNP_chanDepthInfo`), applies median filtering and z-score normalization, and renders a heatmap where rows are clusters ordered by depth and columns are time bins. Uses the inverted Roma colormap (crameri).

## Pipeline Position

Stage 7 (final). Requires `RasterData.mat` from stage 4 and `NPclu.mat` from stage 2.

## Dependencies

- `utils/psth.m` — computes peri-stimulus time histograms
- `utils/sortKSSpX.m` — sorts spike rasters by reaction time
- `utils/getNP_chanDepthInfo.m` — retrieves channel depth/position metadata
- `valid_recordings.xlsx` — used to enumerate recordings if `rec` argument is omitted
