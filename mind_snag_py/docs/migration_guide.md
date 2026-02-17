# Migration Guide: MATLAB v1.0 to Python v2.0

## Quick Start

```bash
pip install mind-snag
```

### MATLAB (v1.0)
```matlab
cd /path/to/mind_snag; setup;
cfg = mind_snag_config('data_root', '/data', 'kilosort_venv', '/venv');
pipeline_KS4(cfg, '250224', {'007','009','010'}, 'LPPC_LPFC_modularV1', 1);
```

### Python (v2.0)
```python
from mind_snag import Pipeline, MindSnagConfig

cfg = MindSnagConfig(data_root="/data")
pipeline = Pipeline(cfg)
pipeline.run(day="250224", recs=["007", "009", "010"],
             tower="LPPC_LPFC_modularV1", np_num=1)
```

### CLI
```bash
mind-snag run --config config.yaml --day 250224 --recs 007 009 010 \
    --tower LPPC_LPFC_modularV1 --np 1
```

## Key Differences

### Configuration

| MATLAB | Python |
|--------|--------|
| `mind_snag_config('key', value)` | `MindSnagConfig(key=value)` |
| `cfg.data_root` (string) | `cfg.data_root` (Path object) |
| `cfg.gpu = 1` (1-indexed) | `cfg.gpu = 0` (0-indexed) |
| `cfg.kilosort_venv` (subprocess) | Not needed (Python API) |
| `.mat` config file | YAML config file |

### Kilosort Execution

MATLAB shelled out to a Python subprocess. Python calls the `kilosort` API directly:

```python
# No virtualenv setup needed - just pip install kilosort
from mind_snag.sorting.run_kilosort4 import run_kilosort4
run_kilosort4(cfg, day, recs, tower, np_num, grouped)
```

### Output Format

| MATLAB | Python |
|--------|--------|
| `.mat` (v7.3/HDF5) | `.h5` (HDF5 with gzip) |
| `NPclu` matrix `[N, 2]` | Separate `spike_times` and `cluster_ids` datasets |
| `SortData` struct array | `frame_NNNN` groups in HDF5 |
| `RasterData` struct | `spike_clu/NNNNNN` datasets |

### Reading Legacy Files

The Python package can read all existing MATLAB outputs:

```python
from mind_snag.io import load_mat
data = load_mat("rec007.LPPC.1.Grouped.NPclu.mat")
spike_times = data["NPclu"][:, 0]
cluster_ids = data["NPclu"][:, 1]
```

### Converting Files

```bash
mind-snag convert rec007.NPclu.mat rec007.NPclu.h5
```

```python
from mind_snag.io.converter import convert_npclu_mat_to_h5
convert_npclu_mat_to_h5("rec007.NPclu.mat")
```

### Indexing

| Concept | MATLAB | Python |
|---------|--------|--------|
| Cluster IDs in NPclu | 1-indexed | 1-indexed (stored), 0-indexed (internal) |
| Channel map | 0-indexed + 1 | 0-indexed |
| GPU device | 1-indexed | 0-indexed |
| Array dimensions | Column-major | Row-major |

### Stitching

```python
from mind_snag.stitching import NeuronStitcher, save_stitch_results

stitcher = NeuronStitcher(cfg, day, recs, tower, np_num, grouped, "Isolated")
result = stitcher.run()
save_stitch_results(cfg, result, output_dir)
```

### Raster Extraction

The repetitive 8 try/catch blocks are now a data-driven loop:

```python
from mind_snag.trials.task_types import TASK_TYPES

# Each TASK_TYPES entry defines:
#   name, py_task_types, primary_event, fallback_event, time_window, ...
# A single loop handles all 8 task types
```

## Module Mapping

| MATLAB file | Python module |
|---|---|
| `mind_snag_config.m` | `mind_snag.config` |
| `pipeline_KS4.m` | `mind_snag.pipeline` |
| `run_kilosort4.m` | `mind_snag.sorting.run_kilosort4` |
| `extract_spikes.m` | `mind_snag.sorting.extract_spikes` |
| `compute_isolation.m` | `mind_snag.curation.compute_isolation` |
| `extract_rasters.m` | `mind_snag.analysis.extract_rasters` |
| `extract_isolated_units.m` | `mind_snag.curation.extract_isolated_units` |
| `fr_heatmap.m` | `mind_snag.visualization.fr_heatmap` |
| `stitch_neurons.m` | `mind_snag.stitching.stitch_neurons` |
| `save_stitch_results.m` | `mind_snag.stitching.save_stitch_results` |
| `loadKSdir.m` | `mind_snag.io.ks_loader` |
| `readNPY.m` | `numpy.load()` (built-in) |
| `psth.m` | `mind_snag.utils.psth` |
| `trialNPSpike.m` + `loadnpspike.m` | `mind_snag.trials.trial_spike` |
| `loadTrials.m` | `mind_snag.trials.load_trials` |
| `clus_channel_infor.m` | `mind_snag.utils.channel_info` |
| `getNP_chanDepthInfo.m` | `mind_snag.utils.channel_info` |
| 6 small utils | `mind_snag.utils.experiment` |

## Stage 5 (Auto-Curation)

Same as MATLAB v1.0: auto-curation is not yet implemented programmatically.
The pipeline prints a warning and skips this stage.
