# examples/

Annotated example scripts showing how to use mind_snag.

## Files

- **`example_single_recording.m`** — Run the full pipeline on one recording. Shows setup, configuration, pipeline execution, running specific stages, and where to find outputs.

- **`example_grouped_recordings.m`** — Run the pipeline in grouped mode (multiple recordings concatenated before sorting). Shows how passing multiple entries in `recs` triggers automatic concatenation.

- **`example_neuron_stitching.m`** — Cross-recording neuron identity matching. Shows how to call `stitch_neurons` directly, inspect the stitch table, save results, and compare different cluster types (`All`, `Good`, `Isolated`).

## Usage

These scripts are not meant to be run as-is. The user should:
1. Copy an example to their working directory
2. Edit the paths (`data_root`, `kilosort_venv`) to match their system
3. Edit the recording parameters (`day`, `recs`, `tower`, `np`)
4. Run section-by-section (cell mode in MATLAB)
