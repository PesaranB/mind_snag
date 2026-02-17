# mind_snag

A MATLAB pipeline for Neuropixel spike sorting, curation, and cross-recording neuron stitching. Built around Kilosort4 with two-stage drift correction, automated isolation analysis, and trial-aligned raster extraction.

## Features

- **Kilosort4 execution** - Concatenates SpikeGLX `.bin` files and runs KS4 via Python
- **Spike extraction with drift correction** - Two-stage correction: AP → NIDQ → recording timebase
- **Isolation analysis** - PC-based signal-to-noise scoring per cluster per time window
- **Trial-aligned rasters** - Aligns spikes to behavioral events across 8 task types
- **Isolated unit extraction** - Identifies well-isolated units from isolation scores
- **Neuron stitching** - Tracks the same neuron across multiple recordings via waveform and PSTH correlation
- **Visualization** - Depth-sorted firing rate heatmaps

## Requirements

- MATLAB R2022b or later
- Python 3.9+ with `kilosort[gui]==4.0.22` installed in a virtual environment
- SpikeGLX recordings (`.ap.bin` and `.ap.meta` files)

## Installation

```matlab
% Clone the repository
% git clone <repo-url> /path/to/mind_snag

% In MATLAB:
cd /path/to/mind_snag
setup    % adds all directories to the MATLAB path
```

## Quick Start

```matlab
% 1. Setup (once per session)
cd /path/to/mind_snag
setup

% 2. Configure
cfg = mind_snag_config( ...
    'data_root',     '/path/to/monkey/data', ...
    'kilosort_venv', '/path/to/kilosort/venv' ...
);

% 3. Run the full pipeline on grouped recordings
day   = '250224';
recs  = {'007', '009', '010'};
tower = 'LPPC_LPFC_modularV1';
np    = 1;
pipeline_KS4(cfg, day, recs, tower, np);

% 4. Or run specific stages
pipeline_KS4(cfg, day, recs, tower, np, {'extract', 'isolation', 'rasters'});
```

## Neuron Stitching

After running the pipeline on multiple recordings, identify the same neurons across sessions:

```matlab
stitch_table = stitch_neurons(cfg, day, recs, tower, np, 0, 'Isolated');
% Returns [N x numRecs] matrix: each row is one neuron, columns are recordings
% Values are cluster IDs; NaN = neuron not found in that recording
```

## Expected Data Layout

```
data_root/
├── {day}/                              # e.g. 250224/
│   ├── valid_recordings.xlsx           # recording metadata
│   ├── spikeglx_data/
│   │   ├── {rec}/                      # e.g. 007/
│   │   │   └── {rec}_imec{N}/
│   │   │       ├── {rec}_imec{N}.ap.bin
│   │   │       └── {rec}_imec{N}.ap.meta
│   │   └── grouped_recordings.{tower}.{np}/    # created by pipeline
│   │       └── group{rec1}_{rec2}_KS4/         # Kilosort4 output
│   └── {rec}/                          # output directory per recording
│       ├── rec{rec}.{tower}.{np}.{GroupFlag}.NPclu.mat
│       └── KSsave_KS4/
│           ├── rec{rec}.{tower}.{np}.{clu}.{GroupFlag}.SortData.mat
│           └── rec{rec}.{tower}.{np}.{clu}.{GroupFlag}.RasterData.mat
```

### Input Files

| File | Description |
|------|-------------|
| `{rec}_imec{N}.ap.bin` | Raw SpikeGLX action potential binary |
| `{rec}_imec{N}.ap.meta` | SpikeGLX metadata (sampling rate, channel count, drift model) |
| `valid_recordings.xlsx` | Maps recording numbers to SpikeGLX rec names and probe info |

### Output Files

| File | Description |
|------|-------------|
| `NPclu.mat` | Drift-corrected spike times + cluster assignments (`NPclu`, `Clu_info`, `KSclu_info`) |
| `SortData.mat` | Per-cluster isolation features (PC scores, SNR, waveform shape) |
| `RasterData.mat` | Trial-aligned spike rasters across task types |

## Configuration

All settings are controlled via `mind_snag_config`:

```matlab
cfg = mind_snag_config();           % defaults
cfg = mind_snag_config('key', val); % override specific fields
cfg = mind_snag_config('saved.mat');% load from file
```

Key settings:

| Field | Default | Description |
|-------|---------|-------------|
| `data_root` | `''` | Root directory for experimental data |
| `kilosort_venv` | `''` | Python virtualenv with Kilosort4 |
| `gpu` | `1` | GPU device index for Kilosort |
| `ks_version` | `4` | Kilosort version (4 or 2.5) |
| `curation.l_ratio_threshold` | `0.2` | L-ratio threshold for curation |
| `curation.isi_violation_rate` | `0.2` | ISI violation rate threshold |
| `stitching.fr_corr_threshold` | `0.85` | PSTH correlation threshold for stitching |
| `stitching.wf_corr_threshold` | `0.85` | Waveform correlation threshold for stitching |
| `stitching.min_recordings` | `2` | Minimum recordings a neuron must appear in |
| `stitching.channel_range` | `10` | Electrode range for neighbor search |

Save and reload configurations:
```matlab
mind_snag_save_config(cfg, 'my_config.mat');
cfg = mind_snag_config('my_config.mat');
```

## Pipeline Stages

| # | Stage | Function | Description |
|---|-------|----------|-------------|
| 1 | Kilosort | `run_kilosort4` | Concatenate `.bin` files, run KS4 |
| 2 | Extract | `extract_spikes` | Load KS4 output, apply drift correction |
| 3 | Isolation | `compute_isolation` | PC features, signal-to-noise per cluster |
| 4 | Rasters | `extract_rasters` | Trial-aligned spikes per task type |
| 5 | Curation | *(pending)* | Threshold-based unit classification |
| 6 | Iso Units | `extract_isolated_units` | Identify well-isolated units |
| 7 | Heatmap | `fr_heatmap` | Depth-sorted firing rate visualization |

Each stage depends on the previous. Use the `stages` parameter to run a subset:
```matlab
pipeline_KS4(cfg, day, recs, tower, np, {'extract', 'isolation'});
```

## Package Structure

```
mind_snag/
├── pipeline_KS4.m              # Main pipeline entry point
├── Auto_Stitching_V2.m         # Stitching wrapper (run + save)
├── setup.m                     # Path setup script
├── sorting/                    # Kilosort execution, spike extraction
│   ├── run_kilosort4.m
│   └── extract_spikes.m
├── curation/                   # Isolation analysis, unit extraction
│   ├── compute_isolation.m
│   └── extract_isolated_units.m
├── analysis/                   # Trial-aligned rasters
│   └── extract_rasters.m
├── stitching/                  # Cross-recording neuron matching
│   ├── stitch_neurons.m
│   └── save_stitch_results.m
├── visualization/              # Heatmaps, plots
│   └── fr_heatmap.m
├── utils/                      # Shared utilities
│   ├── loadKSdir.m, readNPY.m, readNPYheader.m
│   ├── loadTrials.m, trialNPSpike.m
│   ├── psth.m, sortKSSpX.m, getRasters.m
│   ├── clus_channel_infor.m, getNP_chanDepthInfo.m
│   └── ...
├── config/                     # Configuration
│   ├── mind_snag_config.m
│   └── mind_snag_save_config.m
├── examples/                   # Usage examples
│   ├── example_single_recording.m
│   ├── example_grouped_recordings.m
│   └── example_neuron_stitching.m
├── README.md
└── LICENSE
```

## Grouped vs Non-Grouped Mode

- **Non-grouped** (`length(recs) == 1`): Each recording is spike-sorted independently
- **Grouped** (`length(recs) > 1`): Multiple `.bin` files are concatenated before sorting, then spike times are split back per-recording using duration offsets. This improves template estimation for same-session recordings.

The pipeline auto-detects grouped mode based on the number of recordings passed.

## Key Concepts

- **Two-stage drift correction**: Spike times are corrected from the AP timebase to NIDQ, then from NIDQ to recording timebase, using linear model weights stored in `.ap.meta` files.
- **Channel selection**: Best channel per cluster is determined by a weighted combination of waveform energy and PC feature coverage (see `clus_channel_infor.m`).
- **Trial types**: Parsed from `PyTaskType` field: `delayed_saccade` (CO), `luminance_reward_selection` (Lum), `delayed_reach`/`gaze_anchoring` (Reach), plus touch, doublestep, and null variants.

## License

MIT License. See [LICENSE](LICENSE).
