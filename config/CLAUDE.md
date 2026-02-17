# config/

Configuration management for the mind_snag pipeline.

## Files

- **`mind_snag_config.m`** — Creates or loads the `cfg` struct that every pipeline function takes as its first argument. Supports three modes:
  1. `mind_snag_config()` — returns defaults (paths empty, must be filled in)
  2. `mind_snag_config('key', value, ...)` — override specific fields
  3. `mind_snag_config('saved.mat')` — load from a previously saved `.mat` file

  Nested fields are supported via dot notation: `mind_snag_config('curation.l_ratio_threshold', 0.3)`.

- **`mind_snag_save_config.m`** — Saves a `cfg` struct to a `.mat` file for reuse across sessions.

## Config Fields

| Field | Type | Purpose |
|-------|------|---------|
| `data_root` | string | Root data directory (replaces `MONKEYDIR` global) |
| `output_root` | string | Output directory (defaults to `data_root`) |
| `kilosort_venv` | string | Python virtualenv path for KS4 |
| `kilosort_script` | string | Path to `Run_kilosort4.py` (auto-detected) |
| `probe_file` | string | `.prb` channel map file (auto-detected) |
| `gpu` | int | GPU device index (default 1) |
| `ks_version` | int | Kilosort version: 4 or 2.5 |
| `curation.*` | struct | Curation thresholds (l_ratio, isi, t_ratio) |
| `stitching.*` | struct | Stitching thresholds (fr_corr, wf_corr, min_recordings, channel_range) |
| `raster.*` | struct | Raster settings (time_window, smoothing) |
| `isolation.*` | struct | Isolation settings (window_sec) |

## Design

The `cfg` struct is the central mechanism that replaced global variables (`MONKEYDIR`, `MONKEYNAME`, `MONKEYRECDIR`). Every function receives it explicitly rather than depending on invisible global state.
