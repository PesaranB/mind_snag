# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

mind_snag is a Neuropixel spike sorting, curation, and cross-recording neuron stitching package. It wraps Kilosort4 and provides a 7-stage pipeline from raw SpikeGLX data to trial-aligned rasters and isolation-scored units. The repo contains two implementations:

- **MATLAB v1.0** (root directory) — 28 functions, ~3700 lines
- **Python v2.0** (`mind_snag_py/`) — 28 modules, ~2700 lines, pip-installable

## Repository Structure

```
mind_snag/
├── pipeline_KS4.m          # MATLAB entry point - orchestrates all 7 stages
├── Auto_Stitching_V2.m     # Stitching wrapper (stitch + save)
├── setup.m                 # Run once per MATLAB session to add dirs to path
├── sorting/                # run_kilosort4, extract_spikes
├── curation/               # compute_isolation, extract_isolated_units
├── analysis/               # extract_rasters
├── stitching/              # stitch_neurons, save_stitch_results
├── visualization/          # fr_heatmap
├── utils/                  # loadKSdir, readNPY, psth, trialNPSpike, etc.
├── config/                 # mind_snag_config, mind_snag_save_config
├── examples/               # 3 example scripts
└── mind_snag_py/           # Python v2.0 package
    ├── pyproject.toml
    ├── config/example_config.yaml
    ├── docs/               # migration_guide.md, data_format.md
    ├── src/mind_snag/      # 28 modules (config, io, sorting, curation, etc.)
    └── tests/              # 41 unit tests
```

## Architecture

Both versions share the same architecture. All functions take a `cfg` object (MATLAB struct / Python dataclass) as their first argument. This replaces the old global variables (`MONKEYDIR`, `MONKEYNAME`). Key fields: `cfg.data_root`, `cfg.stitching.*`, `cfg.curation.*`.

Pipeline stages are sequential (each depends on previous outputs):
1. `run_kilosort4` → KS4 output in `grouped_recordings.{tower}.{np}/`
2. `extract_spikes` → `NPclu.mat` / `.h5` (drift-corrected spike times)
3. `compute_isolation` → `SortData.mat` / `.h5` (PC features, isolation scores)
4. `extract_rasters` → `RasterData.mat` / `.h5` (trial-aligned spikes)
5. Auto-curation → (pending: still requires GUI)
6. `extract_isolated_units` → updates NPclu with `IsoClu_info`
7. `fr_heatmap` → visualization

## Data Path Convention

- Input: `{data_root}/{day}/spikeglx_data/{rec}/{rec}_imec{N}/`
- Output: `{data_root}/{day}/{rec}/` (NPclu, events)
- KS4 output: `{data_root}/{day}/spikeglx_data/grouped_recordings.{tower}.{np}/group{recs}_KS4/`
- Per-cluster: `{data_root}/{day}/{rec}/KSsave_KS4/` (SortData, RasterData)

## Key Parameters

- `day`: YYMMDD string (e.g. `'250224'`)
- `recs`: cell array of recording numbers (e.g. `{'007','009','010'}`)
- `tower`: recording setup name (e.g. `'LPPC_LPFC_modularV1'`)
- `np`: probe number (1 or 2)
- `grouped`: 0 = individual recordings, 1 = concatenated (auto-detected by pipeline)

## Grouped vs Non-Grouped

Grouped mode concatenates multiple `.bin` files before KS4 sorting, then splits spike times back per-recording. The `GroupFlag` string ('Grouped' or 'NotGrouped') appears in all output filenames.

## Two-Stage Drift Correction

Applied in `extract_spikes`: AP timebase → NIDQ timebase → recording timebase, using linear model weights from `.ap.meta` files.

## Stitching Algorithm

`stitch_neurons` identifies the same neuron across recordings by:
1. Finding clusters within ±`channel_range` electrodes of each unique channel
2. Computing pairwise Pearson correlation of PSTH and waveform
3. Stitching if both FR corr ≥ threshold AND waveform corr ≥ threshold
4. Deduplicating and filtering by minimum recording count

## Running (MATLAB)

```matlab
cd /path/to/mind_snag; setup;
cfg = mind_snag_config('data_root', '/data', 'kilosort_venv', '/venv');
pipeline_KS4(cfg, '250224', {'007','009','010'}, 'LPPC_LPFC_modularV1', 1);
```

## Running (Python)

```bash
pip install -e mind_snag_py/
```

```python
from mind_snag import Pipeline, MindSnagConfig

cfg = MindSnagConfig(data_root="/data")
pipeline = Pipeline(cfg)
pipeline.run(day="250224", recs=["007", "009", "010"],
             tower="LPPC_LPFC_modularV1", np_num=1)
```

```bash
mind-snag run --config config.yaml --day 250224 --recs 007 009 010 \
    --tower LPPC_LPFC_modularV1 --np 1
```

## Python Package Details

- **Config**: Nested dataclasses (`MindSnagConfig`) with YAML serialization. GPU is 0-indexed (MATLAB was 1-indexed).
- **I/O**: Reads legacy `.mat` (v7 and v7.3/HDF5). Writes new outputs as `.h5` with gzip compression.
- **Kilosort**: Calls the `kilosort` Python API directly — no virtualenv/subprocess needed.
- **Indexing**: 0-indexed internally, 1-indexed in stored files for backward compatibility.
- **Tests**: `pytest mind_snag_py/tests/` — 41 tests covering config, I/O, sorting, stitching, paths, PSTH.
- **Docs**: `mind_snag_py/docs/migration_guide.md` (MATLAB→Python mapping), `data_format.md` (HDF5 schemas).
