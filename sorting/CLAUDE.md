# sorting/

Kilosort4 execution and spike extraction from raw SpikeGLX data.

## Files

- **`run_kilosort4.m`** — Concatenates `.ap.bin` files from multiple recordings into a single binary, then invokes Kilosort4 via a Python virtualenv. Handles both grouped (multi-recording concatenation) and single-recording modes. Creates the `grouped_recordings.{tower}.{np}/` directory structure under `spikeglx_data/`.

- **`extract_spikes.m`** — Loads Kilosort output (spike times, templates, cluster assignments) and applies two-stage drift correction: AP timebase → NIDQ timebase → recording timebase using linear model weights from `.ap.meta` files. Saves `NPclu.mat` with drift-corrected spike times, cluster-to-channel mapping, and PC features.

## Pipeline Position

These are stages 1 and 2 of the pipeline. `run_kilosort4` must complete before `extract_spikes` can run. All downstream stages (`compute_isolation`, `extract_rasters`, etc.) depend on the `NPclu.mat` produced by `extract_spikes`.

## Key Concepts

- **Grouped mode**: When `grouped=1`, multiple `.bin` files are memory-mapped and concatenated into `combined_ap_group{recs}.bin`. Spike times are later split back per-recording using duration offsets read from metadata.
- **Drift correction**: SpikeGLX records drift model weights in `.ap.meta`. The correction chain is AP → NIDQ → REC, applied as linear interpolation of timing offsets.
- **KS output directory**: `{data_root}/{day}/spikeglx_data/grouped_recordings.{tower}.{np}/group{recs}_KS4/`

## Dependencies

- `cfg.kilosort_venv` — Python virtualenv with `kilosort[gui]==4.0.22`
- `cfg.kilosort_script` — Path to `Run_kilosort4.py`
- `cfg.probe_file` — `.prb` channel map file
- `utils/loadKSdir.m` — reads KS4 NPY output files
- `utils/clus_channel_infor.m` — determines best channel per cluster
