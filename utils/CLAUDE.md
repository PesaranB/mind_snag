# utils/

Shared utility functions used across the pipeline. These were consolidated from 4+ external directories into this single location.

## Kilosort I/O

- **`loadKSdir.m`** — Loads all Kilosort output from a directory (spike times, templates, clusters, amplitudes, PC features, channel map). Entry point for reading KS4 results.
- **`readNPY.m`** — Reads NumPy `.npy` binary files into MATLAB arrays.
- **`readNPYheader.m`** — Parses `.npy` file headers (shape, dtype, byte order).
- **`readClusterGroupsCSV.m`** — Reads `cluster_groups.csv` / `cluster_group.tsv` files with cluster quality labels (noise/mua/good/unsorted).
- **`loadParamsPy.m`** — Parses Kilosort/Phy `params.py` files into MATLAB structs.

## Trial Data and Spike Alignment

- **`loadTrials.m`** — Loads behavioral trial structures from `{data_root}/{day}/mat/Trials.mat`. Supports filtering by recording number.
- **`trialNPSpike.m`** — Loads Neuropixel spike data aligned to behavioral events. Handles KS4, KS2.5, and legacy versions. Calls `loadnpspike` for per-trial extraction.
- **`loadnpspike.m`** — Extracts spike times for a single trial and cluster, relative to an event time.
- **`loadExperiment.m`** — Loads experiment definition from `.experiment.mat` files.
- **`dayrecs.m`** — Lists all recording directories for a given day.
- **`getRec.m`** — Extracts recording identifiers from a Trials struct array.
- **`findSys.m`** — Maps system/tower names to indices in the Trials struct.
- **`get_neuropixel_microdrives.m`** — Filters experiment hardware to find Neuropixel probes.

## Analysis Helpers

- **`psth.m`** — Computes peri-stimulus time histogram with Gaussian smoothing. Can also plot a raster + rate overlay.
- **`sortKSSpX.m`** — Sorts spike rasters by reaction time (ascending).
- **`getRasters.m`** — Converts spike cell arrays into X/Y scatter coordinates for raster plots.
- **`clus_channel_infor.m`** — Determines the best (max energy) and worst channel per cluster using weighted combination of waveform energy and PC feature coverage.
- **`getNP_chanDepthInfo.m`** — Returns channel depth, position, electrode numbers, and coordinates for a Neuropixel probe. Reads from experiment hardware metadata.

## Origin

| Function | Original location |
|----------|-------------------|
| `loadKSdir`, `readClusterGroupsCSV`, `loadParamsPy` | `/vol/brains/raid/analyze/toolboxes/spikes/` |
| `readNPY`, `readNPYheader` | `/vol/brains/raid/analyze/toolboxes/npy-matlab/` |
| `loadTrials` | `/vol/brains/raid/analyze/load/` |
| `trialNPSpike` | `/vol/brains/raid/analyze/trial/` |
| `psth` | `/vol/brains/raid/analyze/plot/` |
| `clus_channel_infor` | `/vol/brains/raid/analyze/utils/` |
| `sortKSSpX`, `getRasters`, `getNP_chanDepthInfo` | `/vol/brains/bd5/pesaranlab/.../betty/` |
| `loadnpspike`, `loadExperiment` | `/vol/brains/raid/analyze/load/` |
| `dayrecs` | `/vol/brains/raid/analyze/day/` |
| `getRec`, `get_neuropixel_microdrives` | `/vol/brains/raid/analyze/get/` |
| `findSys` | `/vol/brains/raid/analyze/sess/` |
