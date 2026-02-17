# curation/

Isolation analysis and unit quality assessment.

## Files

- **`compute_isolation.m`** — For each cluster, extracts PC features on the max-amplitude channel, segments the recording into time windows (`cfg.isolation.window_sec`, default 100s), and computes an isolation score: `|mean(unit_PC) - mean(noise_PC)| / std(noise_PC)`. Identifies co-recorded units on the same electrode. Saves per-cluster `SortData.mat` files with waveforms, PC features, and isolation metrics per time window.

- **`extract_isolated_units.m`** — Scans all `SortData.mat` files for units with `UnitIso == 1`, collects their spike data from `NPclu`, and appends `NPisoclu` (isolated spike times) and `IsoClu_info` (isolated cluster-to-channel mapping) back into `NPclu.mat`.

## Pipeline Position

Stage 3 (`compute_isolation`) and stage 6 (`extract_isolated_units`). Note the gap: `extract_rasters` (stage 4) and auto-curation (stage 5) run between these two. `extract_isolated_units` requires the `UnitIso` flag set during curation.

## Output Files

- `{data_root}/{day}/{rec}/KSsave_KS4/rec{rec}.{tower}.{np}.{clu}.{GroupFlag}.SortData.mat` — per-cluster isolation data
- Updates to `NPclu.mat` with `NPisoclu` and `IsoClu_info` fields

## Key Concepts

- **Isolation score**: Signal-to-noise ratio of unit PC projections vs noise channel PC projections. Higher = better isolated.
- **Time windows**: The recording is split into chunks to assess stability of isolation over time. A unit must be well-isolated across windows to be classified as isolated.
- **Max vs min channel**: `clus_channel_infor.m` picks the best channel (highest waveform energy weighted by PC coverage) and worst channel (lowest energy, used as noise reference).
