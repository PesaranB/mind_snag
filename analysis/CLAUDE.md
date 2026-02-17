# analysis/

Trial-aligned spike raster extraction.

## Files

- **`extract_rasters.m`** — Aligns spikes to behavioral trial events for each cluster. Loads trial data via `loadTrials`, calls `trialNPSpike` to extract spikes in a time window around each event, and saves per-cluster `RasterData.mat` files. Also extracts rasters for neighboring clusters on the same electrode (stored as `OtherClu`/`OtherSpikeClu`).

## Pipeline Position

Stage 4. Requires `NPclu.mat` from `extract_spikes` (stage 2). The raster data is used by `extract_isolated_units` (stage 6) and `fr_heatmap` (stage 7), and by the stitching algorithm for PSTH correlation.

## Task Types

Trials are categorized by `PyTaskType` from the behavioral system:

| PyTaskType | Short name | Alignment event | Time window |
|------------|------------|-----------------|-------------|
| `delayed_saccade` | CO | TargsOn | [-300, 500] ms |
| `luminance_reward_selection` | Lum | TargsOn | [-300, 500] ms |
| `delayed_reach` / `gaze_anchoring` | Reach | Multiple (TargsOn, Go, ReachStart) | [-400, 400] ms |
| `simple_touch_task` | Touch | Pulse_start | [-300, 500] ms |
| `doublestep_saccade_fast` | Saccade | TargsOn | [-300, 500] ms |
| `null` | Null | TargsOn | [-300, 500] ms |

## Output Files

- `{data_root}/{day}/{rec}/KSsave_KS4/rec{rec}.{tower}.{np}.{clu}.{GroupFlag}.RasterData.mat`

## Dependencies

- `utils/loadTrials.m` — loads behavioral trial structures
- `utils/trialNPSpike.m` — extracts spike times aligned to trial events
- `utils/sortKSSpX.m` — sorts rasters by reaction time (used downstream)
