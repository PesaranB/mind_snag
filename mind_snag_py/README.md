# mind_snag

[![GitHub release](https://img.shields.io/github/v/release/PesaranB/mind_snag)](https://github.com/PesaranB/mind_snag/releases/latest)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Neuropixel spike sorting, curation, and cross-recording neuron stitching. Python port of the [MATLAB mind_snag package](https://github.com/PesaranB/mind_snag).

## Installation

```bash
pip install mind-snag
```

Or from source:

```bash
git clone https://github.com/PesaranB/mind_snag.git
cd mind_snag/mind_snag_py
pip install -e ".[dev]"
```

## Quick Start

### CLI

```bash
mind-snag run --config config.yaml --day 250224 --recs 007 009 010 \
    --tower LPPC_LPFC_modularV1 --np 1
```

### Python API

```python
from mind_snag import Pipeline, MindSnagConfig

cfg = MindSnagConfig(data_root="/data", kilosort_venv="/venv")
pipeline = Pipeline(cfg)
pipeline.run(day="250224", recs=["007", "009", "010"],
             tower="LPPC_LPFC_modularV1", np_num=1)
```

## Pipeline Stages

1. **run_kilosort4** - Run KS4 via Python API with optional .bin concatenation
2. **extract_spikes** - Two-stage drift correction, NPclu output
3. **compute_isolation** - PC-based SNR isolation scoring
4. **extract_rasters** - Trial-aligned rasters for 8 task types
5. **ks4_curation_gui** - Interactive Python GUI for cluster review (SNaG port)
6. **extract_isolated_units** - Filter units by isolation score
7. **fr_heatmap** - Firing rate heatmap visualization

## Curation GUI

After running KS4, curate clusters interactively with the SNaG-style GUI:

```bash
# Basic usage (autocorrelogram + firing rate view)
python ks4_curation_gui.py /path/to/kilosort4_output/

# With event-aligned raster + PSTH
python ks4_curation_gui.py /path/to/kilosort4_output/ --events swr_times.npy

# See all options
python ks4_curation_gui.py --help
```

The GUI uses `mind_snag.io.load_ks_dir()` to read KS4 output and memory-maps `pc_features.npy` for on-demand PC scatter plots. Saves phy-compatible `cluster_group.tsv` and a `curation_state.json` for session resume. See the root [README](../README.md#curation-gui-python--snag-port) for full keyboard shortcuts and layout details.

## Data Format

- **Input**: Reads existing MATLAB `.mat` outputs (backward compatible)
- **Output**: HDF5 format with gzip compression

See [docs/data_format.md](docs/data_format.md) for schema details and
[docs/migration_guide.md](docs/migration_guide.md) for migrating from MATLAB.

## Configuration

Copy `config/example_config.yaml` and edit:

```yaml
data_root: /path/to/data
gpu: 0
stitching:
  fr_corr_threshold: 0.3
  wf_corr_threshold: 0.5
  channel_range: 5
  min_rec_count: 2
```

## License

MIT
