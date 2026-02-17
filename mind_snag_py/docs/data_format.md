# Data Format Specification

## Output File Formats

mind_snag v2.0 writes outputs in HDF5 format with gzip compression.
It can also read legacy MATLAB .mat files from v1.0.

## NPclu.h5

Drift-corrected spike data with cluster metadata.

### Datasets

| Dataset | Type | Shape | Description |
|---------|------|-------|-------------|
| `spike_times` | float64 | `[N]` | Drift-corrected spike times (seconds) |
| `cluster_ids` | int64 | `[N]` | Cluster ID per spike (1-indexed for MATLAB compat) |
| `templates` | float64 | `[nTemplates, nTimePoints, nChannels]` | Template waveforms |
| `clu_info` | int64 | `[nClusters, 2]` | `[cluster_id, channel_index]` mapping |
| `ks_clu_info` | int64 | `[nGood, 2]` | Good units only (KS label = 'good') |
| `pc_feat` | float64 | `[N, 3, nLocalChannels]` | PC features per spike |
| `temp_scaling_amps` | float64 | `[N]` | Template scaling amplitudes |
| `iso_spike_times` | float64 | `[M]` | Isolated unit spike times (after stage 6) |
| `iso_cluster_ids` | int64 | `[M]` | Isolated unit cluster IDs |
| `iso_clu_info` | int64 | `[nIso, 2]` | Isolated cluster-to-channel mapping |

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `ks_version` | int | Kilosort version (4) |
| `creation_date` | string | ISO 8601 timestamp |
| `format` | string | `mind_snag_v2` |

## SortData.h5

Isolation analysis per cluster, with one group per time window.

### Structure

```
/
├── attrs: creation_date, format, n_frames
├── frame_0000/
│   ├── attrs: score, unit_iso, clu
│   ├── clu_wf       [nTimePoints]
│   ├── noise_wf     [nTimePoints]
│   ├── unit         [nSpikes, 3]
│   ├── noise        [nSpikes, 3]
│   └── ...
├── frame_0001/
│   └── ...
```

## RasterData.h5

Trial-aligned spike data per cluster.

### Structure

```
/
├── attrs: creation_date, format, clu
├── spike_clu/
│   ├── 000000       [nSpikes_trial_0]
│   ├── 000001       [nSpikes_trial_1]
│   └── ...
├── rt               [nTrials]
├── other_clu        [nOther]
└── other_spike_clu/
    ├── 0000/
    │   ├── 000000   [nSpikes]
    │   └── ...
    └── ...
```

## Stitch Results

### stitch_{day}_{recs}.h5

```
/
├── stitch_table     [nNeurons, nRecs]  (NaN = not found)
├── attrs: day, tower, np_num, num_recs, rec_0, rec_1, ...
```

## Legacy .mat Compatibility

The Python package reads MATLAB v7 and v7.3 (HDF5-based) .mat files.
When reading legacy outputs:
- v7 files are read via `scipy.io.loadmat`
- v7.3 files are read via `h5py` with recursive traversal
- 2D arrays are transposed (MATLAB uses column-major order)
- String fields stored as uint16 arrays are decoded to Python strings

## Indexing Convention

- **Internal**: 0-indexed everywhere in Python
- **NPclu cluster IDs**: 1-indexed in stored files (for backward compat with MATLAB)
- **Channel map**: 0-indexed in stored files (matches Kilosort output)
- Utility functions `_matlab_to_python_index()` and `_python_to_matlab_index()` handle conversion
