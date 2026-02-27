# mind_snag Project Analysis: Dissemination, Integration, and Positioning

> Generated 2026-02-27 from extended planning discussion.
> Covers: dissemination readiness, SpikeInterface integration, cross-recording neuron tracking landscape, stitching enhancements, NHP positioning, and naming.

---

## Table of Contents

1. [Dissemination Readiness Audit](#1-dissemination-readiness-audit)
2. [SpikeInterface Integration Plan](#2-spikeinterface-integration-plan)
3. [Cross-Recording Neuron Tracking Landscape](#3-cross-recording-neuron-tracking-landscape)
4. [Enhancing Stitch Output Beyond Binary](#4-enhancing-stitch-output-beyond-binary)
5. [Positioning: mind_snag vs UnitMatch](#5-positioning-mind_snag-vs-unitmatch)
6. [The Non-Rigid Drift Argument](#6-the-non-rigid-drift-argument)
7. [Event-Triggered Average Extension](#7-event-triggered-average-extension)
8. [Empirical UnitMatch Comparison](#8-empirical-unitmatch-comparison)
9. [Naming](#9-naming)
10. [References](#10-references)

---

## 1. Dissemination Readiness Audit

### What IS configurable

- `data_root` / `output_root` paths
- All curation, stitching, and raster thresholds
- GPU index, KS4 parameters

### What is hardcoded (would break for other labs)

#### Directory structure (Python `utils/paths.py`, MATLAB `run_kilosort4.m`)

- `spikeglx_data/`, `grouped_recordings.{tower}.{np}/`, `KSsave_KS4/`, `mat/`
- Output suffixes: `NPclu`, `SortData`, `RasterData`
- `GroupFlag` strings (`"Grouped"` / `"NotGrouped"`)

#### SpikeGLX-specific naming

- Probe directories: `{rec}_imec{N}/`
- Bin files: `{rec}_t0.imec{N}.ap.bin`
- Metadata: `.ap.meta.mat`, `.nidq_meta.mat`
- 385-channel default (NP1 probe)

#### Lab-specific behavioral conventions

- **Task types** hardcoded to Pesaran Lab tasks (`task_types.py:40-125`, `extract_rasters.m:87-96`): CO, Lum, Reach, GAF, Saccade, Touch, Null
- **Event field names** (TargsOn, SaccStart, disGo) are lab-specific
- **Trial file** assumed at `{data_root}/{day}/mat/Trials.mat`
- **Experiment metadata** assumed at `rec{rec}.experiment.mat`
- **Excel lookup** at `{data_root}/excel/valid_recordings.xlsx` (fatal assert in MATLAB)

#### Legacy globals

- MATLAB utilities fall back to `MONKEYDIR` global variable (`getNP_chanDepthInfo.m`, `trialNPSpike.m`, `dayrecs.m`, `loadExperiment.m`)

### Affected files (both codebases)

| Area | MATLAB | Python |
|------|--------|--------|
| Path construction | `run_kilosort4.m`, `extract_spikes.m` | `utils/paths.py`, `run_kilosort4.py`, `extract_spikes.py` |
| Task definitions | `extract_rasters.m:87-96` | `trials/task_types.py:40-125` |
| Trial loading | `utils/loadTrials.m:15` | `trials/load_trials.py:36` |
| Experiment metadata | `utils/loadExperiment.m:33` | `utils/experiment.py:30` |
| Channel info | `utils/getNP_chanDepthInfo.m:28-30` | `channel_info.py:78` |
| Config | `config/mind_snag_config.m` | `config.py` |

### Required changes for dissemination

1. **Parameterize path patterns** in `MindSnagConfig`: `spikeglx_dirname`, `ks_output_pattern`, `trials_file_path`, `event_file_pattern`
2. **Make task types configurable** via YAML (or separate `tasks.yaml`) so other labs can define their own behavioral tasks and event fields
3. **Abstract SpikeGLX assumptions** for labs using different acquisition systems or probe types
4. **Remove `MONKEYDIR` fallbacks** — require explicit `cfg` everywhere
5. **Soften fatal asserts** (MATLAB Excel lookup at `run_kilosort4.m:180`)

---

## 2. SpikeInterface Integration Plan

### Overlap map

| mind_snag stage | SI equivalent |
|-----------------|---------------|
| Read SpikeGLX `.bin` files | `si.read_spikeglx()` — also handles Open Ephys, Intan, Plexon, 30+ formats |
| `run_kilosort4` (hardcoded paths, 385 ch) | `si.run_sorter("kilosort4", recording)` — standardized I/O, auto probe geometry |
| `extract_spikes` (drift correction, spike times) | SI postprocessing + `BaseSorting` object |
| `compute_isolation` (PC features, isolation score) | `si.qualitymetrics` — isolation distance, L-ratio, d-prime, silhouette, SNR, ISI violations, amplitude cutoff, drift metrics |
| `loadKSdir`, `readNPY` | `si.read_kilosort()` |

### What mind_snag does that SI does NOT

- Cross-recording neuron stitching (core novel contribution)
- Lab-specific trial alignment (extract_rasters, behavioral task types)
- The curation GUI (`ks4_curation_gui.py`)
- Grouped recording concatenation + split-back logic

### Integration steps

**Step 1: Use SI as the I/O layer (Python side).** Replace hardcoded SpikeGLX path logic with SI extractors. Solves the file naming problem for dissemination.

```python
recording = si.read_spikeglx(folder, stream_id="imec0.ap")
# Or for other labs:
recording = si.read_openephys(folder)
```

Affected: `run_kilosort4.py`, `extract_spikes.py`, `utils/paths.py`

**Step 2: Use SI to run KS4.** Replace direct kilosort API calls with `si.run_sorter()`. Enables trivial sorter swapping (KS3, MountainSort, SpykingCircus).

```python
sorting = si.run_sorter("kilosort4", recording, output_folder=ks_dir)
```

Affected: `run_kilosort4.py`

**Step 3: Use SI quality metrics alongside/instead of custom isolation.** SI computes isolation distance, L-ratio, silhouette score, SNR, ISI violations, and more. Option to replace or augment `compute_isolation`.

Affected: `compute_isolation.py`, `curation/compute_isolation.m` (MATLAB stays as-is)

**Step 4: Keep unique stages, feed them SI objects.** Stitching, raster extraction, and curation GUI consume SI's `Recording`/`Sorting` objects instead of raw file paths.

**Step 5: MATLAB side — lighter integration.** MATLAB can't use SI directly. Options: SI file format converters to NWB/standard `.mat`; thin Python-to-MATLAB bridge; or accept MATLAB stays SpikeGLX-only while Python becomes format-agnostic.

**Step 6: Export to NWB via SI.** Enables Neurodata Without Borders standard output, increasingly required for data sharing.

### Strategic framing

mind_snag becomes a higher-level tool that uses SpikeInterface for I/O and basic metrics, while contributing its unique stitching algorithm, grouped recording logic, and curation GUI on top.

---

## 3. Cross-Recording Neuron Tracking Landscape

### UnitMatch (Nature Methods 2024)

- **Repo**: https://github.com/EnnyvanBeest/UnitMatch
- **Languages**: MATLAB (63%) + Python (UnitMatchPy, including DeepUnitMatch)
- **Algorithm**: Naive Bayes classifier on 6 waveform features: Decay (D), Waveform (W), Amplitude (A), Centroid (C), Volatility (V), Route (R). Outputs match probabilities. Processes all recordings from a probe simultaneously.
- **Input**: NPY files of average waveforms per unit per recording (from Kilosort output)
- **Output**: Matching table with similarity scores + UniqueIDConversion struct
- **Validation**: 18 chronically implanted mice, head-fixed. Up to 235 days, 1350 recordings. ISI histogram AUC 0.88 across days. Population coupling AUC 0.92.
- **Species**: Mouse only. No primate data. No discussion of NHP applicability.
- **Drift handling**: Rigid population-level correction (median centroid displacement)
- **Acute control**: 4.0 +/- 2.8% match rate on daily reinsertion — demonstrates failure when probe position changes
- **Key limitation**: Only 31.3 +/- 11.2% of neurons matched across consecutive days even in optimal (chronic mouse) conditions

### EMD Neuron Tracking (eLife 2024)

- **Repo**: https://github.com/AugustineY07/Neuron_Tracking
- **Authors**: Yuan, Colonell, Lebedeva, Okun, Charles, Harris (Janelia)
- **Algorithm**: Earth Mover's Distance combining spatial location + L2 waveform distance. Two-stage: rigid drift correction first, then non-rigid unit assignment.
- **Performance**: 84% average recovery rate. 90% for <1 week. 78% for 5-7 weeks. 99% accuracy <1 week.
- **Key distinction from UnitMatch**: Explicitly models non-rigid drift via EMD framework
- **Species**: Mouse only (chronic Neuropixels)

### KIASORT (PMC 2025)

- **Paper**: https://pmc.ncbi.nlm.nih.gov/articles/PMC12338522/
- **Language**: Python, outputs HDF5
- **Algorithm**: Hybrid PCA-UMAP + SVM classifiers with per-neuron drift tracking (geometry-free). Cross-channel spike transfer.
- **Key relevance**: This is a spike sorter (KS4 alternative), not a post-hoc stitcher. But its per-neuron drift tracking addresses the heterogeneous drift problem within sessions.
- **Performance**: 5-15% more high-quality units than KS4 under heterogeneous drift

### Power Pixels (bioRxiv 2025)

- **Repo**: https://github.com/NeuroNetMem/PowerPixelsPipeline
- **Authors**: Meijer & Battaglia
- **Not a stitching tool** — a turnkey Neuropixels pipeline integrating Bombcell + UnitRefine + IBL quality criteria. Shows the field's direction: integrated pipelines.

---

## 4. Enhancing Stitch Output Beyond Binary

### Current state: what gets thrown away

The algorithm (`stitch_neurons.py:304-315`, MATLAB lines 275-288) computes rich pairwise data but discards almost everything:

1. FR correlations against every candidate — computed, only `argmax` kept
2. Waveform correlations against every candidate — computed, discarded
3. Second-best matches — gone
4. Below-threshold matches that were close — gone
5. The correlation values for accepted matches — gone (only cluster ID stored)

Final output: `stitch_table` — an `[N x num_recs]` matrix of cluster IDs with NaN for missing. No scores, no confidence, no alternatives.

### Proposed enhancements

#### 4.1 Store match scores alongside cluster IDs

For every accepted stitch, save the FR correlation and waveform correlation. Already computed, just not stored.

Output becomes three parallel matrices:
- `stitch_table` — cluster IDs (as now)
- `fr_corr_table` — FR correlation per match
- `wf_corr_table` — waveform correlation per match

**Effort**: Trivial. **Impact**: High (enables all downstream analyses).

#### 4.2 Compute a composite match probability

Convert FR and waveform correlations to a joint confidence score (geometric mean, or logistic model on pairwise distance distributions). Report confidence per pairwise stitch.

Directly addresses UnitMatch comparison: "we also output probabilities, using both waveform AND functional evidence."

**Effort**: Small. **Impact**: High for review.

#### 4.3 Store the full candidate ranking (top-K)

For each cluster in each recording, store the top-K matches with their FR and waveform correlation values. Enables:

- Reviewer inspection: "second-best match had r=0.81, well below the best at r=0.95"
- Confidence margin: difference between best and second-best match
- Post-hoc re-stitching at different thresholds without re-running

**Effort**: Small change to inner loop. **Impact**: High.

#### 4.4 Add spatial distance as a third feature

UnitMatch and EMD both use spatial position explicitly. mind_snag uses `channel_range` as a binary gate. Instead:

- Compute actual electrode distance between matched clusters
- Store as third score dimension
- Weight closer matches higher in composite probability

**Effort**: Moderate. **Impact**: Moderate.

#### 4.5 Compute within-neuron stability metrics

For each stitched neuron, compute and store:

- Waveform stability across recordings (variance of waveform correlations)
- Firing rate stability across recordings
- Channel drift: did it shift channels between recordings?

**Effort**: Moderate. **Impact**: High for paper figures.

#### 4.6 Add null distribution / statistical test

The biggest gap vs. UnitMatch: mind_snag's thresholds (0.85, 0.85) are arbitrary.

- For each channel neighborhood, compute distribution of correlations between non-matching clusters (different neurons on nearby channels)
- Report match significance as p-value or z-score against this null
- Enables statement: "this match has p < 0.001 against the null"

**Effort**: Moderate. **Impact**: Highest for review.

### Implementation priority

1. Store FR + WF correlation values — trivial, already computed
2. Top-K candidate ranking — small inner loop change
3. Composite confidence score — straightforward post-processing
4. Null distribution / p-values — moderate effort, high review impact
5. Spatial distance feature — moderate effort
6. Stability metrics — straightforward once scores are stored

Items 1-3: ~1 day across both codebases. Items 4-6: more substantial but strongest review impression.

---

## 5. Positioning: mind_snag vs UnitMatch

### The recording paradigm gap

| Scenario | UnitMatch | mind_snag |
|----------|-----------|-----------|
| Rodent chronic, cross-day (probe cemented, same position) | Designed for this | Not designed for this |
| Rodent chronic, within-day (multiple blocks, same insertion) | Works (trivial case) | Would work |
| Primate acute, cross-day (different insertion each day) | ~4% match rate (fails) | Not designed for this |
| **Primate acute, within-session (multiple task blocks, same insertion, within-session drift)** | Never tested | **Primary niche** |

### NHP recording reality

NHP Neuropixels recordings are overwhelmingly acute:

- Thick dura (1.5-3mm) regrows over weeks, requiring durotomy
- Brain pulsation from cardiac/respiratory cycles: hundreds of micrometers in large craniotomies, "at least an order of magnitude larger relative to rodents"
- Settle time of 30-60 min after insertion as tissue relaxes
- Probe position varies by 150-300 micrometers between sessions (overshoot-then-retract protocol)
- Sessions typically 3-4 hours with multiple task blocks

### Framing: paradigm gap, not species gap

**Do not claim**: "UnitMatch fails on primates" — no empirical evidence for this.

**Do claim**: "mind_snag fills the acute/within-session gap that UnitMatch explicitly cannot address — the dominant recording paradigm in NHP electrophysiology."

The species angle is better framed as: "mind_snag was developed for and validated on NHP acute recordings, a recording paradigm that is underserved by existing tools which were developed for and validated exclusively on chronic rodent recordings."

---

## 6. The Non-Rigid Drift Argument

### The fundamental asymmetry

**UnitMatch philosophy**: Waveform is the neuron's fingerprint. Drift moves all neurons on the probe similarly (rigid correction). Match by correcting for population-level drift, then comparing waveforms.

**mind_snag philosophy**: Drift is non-rigid and neuron-specific. Different neurons at different depths, in different tissue microenvironments, experience different displacement trajectories. Waveform alone cannot reliably track identity when the waveform change itself varies across neurons on the same probe. Therefore, functional evidence (event-triggered activity) is needed as a second, independent channel of identity information.

### Supporting evidence

1. **Non-rigid drift is documented**: "Drifts can be slow, rigid, or non-rigid as a function of the positions of the cells" and "spontaneous drifts can happen locally and non-homogeneously over the whole probe" (eNeuro 2023)

2. **EMD paper models non-rigid drift explicitly**: Two-stage rigid-then-non-rigid correction, acknowledging UnitMatch's rigid-only approach is insufficient (eLife 2024)

3. **Primate brains have more heterogeneous tissue dynamics**: Larger tissue mass + vascular pulsation + dural mechanics create more heterogeneous movement than in mouse. Brain pulsation "at least an order of magnitude larger relative to rodents." This is physically inevitable, not speculative.

4. **Waveform alone has limited power in NHP**: A 2025 J. Neuroscience paper argues waveform + discharge statistics + anatomical layer are all needed to identify neuron types from extracellular recordings in NHP. "Modern recording probes have limited power to resolve neuron identity" from waveform alone.

5. **UnitMatch's own waveform degradation**: Visual fingerprint similarity dropped to 60% after 40 days in mice. In primates, where drift is larger, degradation would be faster and more severe.

### Why dual-evidence tracking addresses this

When non-rigid drift makes waveform matching unreliable, functional activity provides an independent identity channel. Two neurons may have similar waveforms after drift, but if their event-triggered firing patterns differ, they are distinguishable. Conversely, if waveforms diverge due to drift but functional fingerprints remain correlated, identity is preserved.

---

## 7. Event-Triggered Average Extension

### Current: task-triggered PSTH only

The current stitching algorithm correlates PSTH (peri-stimulus time histogram) across recordings. This requires a behavioral task with defined trial events.

### Proposed: physiologically-defined event-triggered averages (ETAs)

Extend identity matching to use firing patterns locked to endogenous neural events:

| Event type | Identity signal | Literature support |
|------------|----------------|-------------------|
| **Sleep spindles** | Cell-type specific phase preferences (pyramidal vs. interneuron fire at different phases) | eLife 2020 (spindle-ripple coupling) |
| **Hippocampal ripples** | Pyramidal cells fire at ripple peak, interneurons fire earlier — timing is a fingerprint | J. Neuroscience 2008 (cell-type specific firing during ripples) |
| **Beta bursts** | In primate motor/prefrontal cortex, putative interneurons and pyramidal cells show unique synchronization to beta vs. theta | Cerebral Cortex 2018 (cell-type specific burst firing) |
| **Theta bursts** | Phase-locking preference characteristic of neuron type | PLOS Biology 2024 (thalamic spindles, Up states, co-ripples) |

### Why this matters

1. **Removes task dependence**: Identity matching works on spontaneous physiological events in any recording (sleep, rest, anesthesia). No behavioral task required.

2. **Richer fingerprint**: Multiple event types provide multiple independent axes of identity evidence. A neuron's relationship to spindles, ripples, and beta bursts collectively form a multi-dimensional functional fingerprint.

3. **Biologically grounded**: "Computational fingerprints that define cell type are robust across diverse stimuli" and "a reliable stream of information about cell type is embedded within the time series of neuronal activity" (Cell 2025).

4. **Complementary to waveform**: Event-triggered activity is independent of waveform shape, providing genuine additional information rather than a redundant measure.

### Implementation

- Detect events (spindles, ripples, beta bursts) from LFP using standard algorithms
- Compute event-triggered spike averages per cluster per event type
- Add ETA correlations as additional features in the matching algorithm alongside PSTH and waveform correlations
- Composite confidence score now incorporates waveform + PSTH + ETA(s)

---

## 8. Empirical UnitMatch Comparison

### Planned validation

Run UnitMatch on NHP Neuropixels data to empirically compare performance. This eliminates speculation about whether UnitMatch works on primate data.

**Within-day comparison** (same insertion, multiple task blocks):
- Run both mind_snag stitching and UnitMatch on the same data
- Compare match rates, false positive rates, and confidence calibration
- Test whether dual-evidence (waveform + PSTH/ETA) catches cases UnitMatch misses
- Test whether PSTH correlation adds value by identifying cases where waveform-only matching produces false positives or false negatives

**Across-day comparison** (if chronic NHP data available):
- Run UnitMatch and mind_snag on cross-day NHP recordings
- Quantify within-session drift in primate data
- Show how non-rigid drift affects waveform-only matching performance

### Expected outcomes

Even if UnitMatch performs reasonably on NHP data:
- Dual-evidence approach should produce higher confidence matches
- Should identify cases where similar waveforms belong to functionally distinct neurons
- Should identify cases where drifted waveforms belong to the same neuron (detectable via correlated PSTH/ETA)

---

## 9. Naming

### Current name limitations

"mind_snag" / "SNaG" does not convey the scientific contribution (dual-evidence neuron tracking across recordings).

### Candidates

| Name | Stands for | Rationale |
|------|-----------|-----------|
| **MINT** | Matching Identity of Neurons across Tracks | Short, memorable, clean acronym. Works in a sentence: "We used MINT to track neurons across task blocks." |
| **STITCH** | Spike Tracking and Identity Through Correlated History | Directly describes the method; "stitching" is already the verb used. Captures PSTH/ETA (correlated history). |
| **FUSE** | Functional and waveform Unified Spike identity Engine | Most conceptually precise. Core argument is fusing waveform + functional evidence. |
| **DRIFT** | Dual-feature Robust Identity Finding across Tracks | Names the problem (drift) and the solution (dual features). |
| **SNAP** | Spike and Neural Activity Pairing | Close to SNaG. Emphasizes pairing of spike waveform + neural activity. |
| **BIND** | Brain Identity by Neural Dynamics | Emphasizes dynamics (not just shape) define identity. |
| **TRACE** | Tracking and Recognition via Activity and Cellular Electrophysiology | Covers both activity (ETA) and waveform. |
| **NeuroPair** | — | Pairing neurons across recordings. |

### Top recommendations

1. **MINT** — short, memorable, and the acronym is clean
2. **STITCH** — directly describes what it does, leverages existing terminology
3. **FUSE** — most conceptually precise for the paper's core argument

---

## 10. References

### Cross-recording neuron tracking

- van Beest et al. "Tracking neurons across days with high-density probes." *Nature Methods* (2024). https://www.nature.com/articles/s41592-024-02440-1
- UnitMatch GitHub: https://github.com/EnnyvanBeest/UnitMatch
- Yuan et al. "Multi-day neuron tracking in high-density electrophysiology recordings using earth mover's distance." *eLife* (2024). https://elifesciences.org/articles/92495
- EMD GitHub: https://github.com/AugustineY07/Neuron_Tracking
- KIASORT. *PMC* (2025). https://pmc.ncbi.nlm.nih.gov/articles/PMC12338522/
- Power Pixels GitHub: https://github.com/NeuroNetMem/PowerPixelsPipeline

### SpikeInterface

- SpikeInterface overview: https://spikeinterface.readthedocs.io/en/latest/overview.html
- SpikeInterface GitHub: https://github.com/SpikeInterface/spikeinterface
- Buccino et al. "SpikeInterface, a unified framework for spike sorting." *eLife* (2020). https://elifesciences.org/articles/61834

### NHP Neuropixels recordings

- Trautmann et al. "Large-scale high-density brain-wide neural recording in nonhuman primates." *Nature Neuroscience* (2025). https://www.nature.com/articles/s41593-025-01976-5
- "Neuropixels for nonhuman primates." *Nature Methods* (2025). https://www.nature.com/articles/s41592-025-02791-3
- Hesse & Bhatt. "3D printed guide tube system for acute Neuropixels probe recordings in non-human primates." *PMC* (2023). https://pmc.ncbi.nlm.nih.gov/articles/PMC10172811/
- Siegle et al. "Inserting a Neuropixels probe into awake monkey cortex: two probes, two methods." *PMC* (2023). https://pmc.ncbi.nlm.nih.gov/articles/PMC10326968/
- Steinmetz et al. "Neuropixels 2.0: A miniaturized high-density probe for stable, long-term brain recordings." *Science* (2021). https://www.science.org/doi/10.1126/science.abf4588

### Non-rigid drift

- Garcia et al. "A modular implementation to handle and benchmark drift correction for high-density extracellular recordings." *eNeuro* (2023). https://www.eneuro.org/content/11/2/ENEURO.0229-23.2023

### Neuron density and species comparisons

- Collins et al. "Neuron densities vary across and within cortical areas in primates." *PNAS* (2010). https://www.pnas.org/doi/10.1073/pnas.1010356107
- Young et al. "Cell and neuron densities in the primary motor cortex of primates." *PMC* (2013). https://pmc.ncbi.nlm.nih.gov/articles/PMC3583034/
- Wildenberg et al. "Primate neuronal connections are sparse in cortex as compared to mouse." *Cell Reports* (2021). https://www.cell.com/cell-reports/fulltext/S2211-1247(21)01156-6
- Loomba et al. "Connectomic comparison of mouse and human cortex." *Science* (2022). https://www.science.org/doi/10.1126/science.abo0924

### Neuron identity from extracellular recordings

- Bhatt et al. "Strategies to decipher neuron identity from extracellular recordings in behaving nonhuman primates." *J. Neuroscience* (2025). https://www.jneurosci.org/content/45/32/e0230252025
- LOLCAT: "A deep learning strategy to identify cell types across species from high-density extracellular recordings." *Cell* (2025). https://www.cell.com/cell/abstract/S0092-8674(25)00110-2
- Paulk et al. "High-density single-unit human cortical recordings using the Neuropixels probe." *Neuron* (2022). https://www.cell.com/neuron/fulltext/S0896-6273(22)00448-2

### Event-triggered neural fingerprints

- Latchoumane et al. "Sleep spindles mediate hippocampal-neocortical coupling during long-duration ripples." *eLife* (2020). https://elifesciences.org/articles/57011
- Le Van Quyen et al. "Cell type-specific firing during ripple oscillations in the hippocampal formation of humans." *J. Neuroscience* (2008). https://pubmed.ncbi.nlm.nih.gov/18550752/
- Voloh et al. "Cell-type specific burst firing interacts with theta and beta activity in prefrontal cortex during attention states." *Cerebral Cortex* (2018). https://academic.oup.com/cercor/article/28/12/4348/4608049
- "Separable global and local beta burst dynamics in motor cortex of primates." *PMC* (2025). https://pmc.ncbi.nlm.nih.gov/articles/PMC12248081/
- Gonzalez et al. "Thalamic spindles and Up states coordinate cortical and hippocampal co-ripples in humans." *PLOS Biology* (2024). https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.3002855

### Spike sorting

- Pachitariu et al. "Spike sorting with Kilosort4." *Nature Methods* (2024). https://www.nature.com/articles/s41592-024-02232-7
