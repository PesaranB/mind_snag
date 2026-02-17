function pipeline_KS4(cfg, day, recs, tower, np, stages)
% PIPELINE_KS4 Master spike sorting pipeline for Neuropixel recordings
%
%   pipeline_KS4(cfg, day, recs, tower, np)
%   pipeline_KS4(cfg, day, recs, tower, np, stages)
%
%   Orchestrates the full spike sorting pipeline:
%     1. Kilosort4 execution (concatenates .bin files, runs KS4)
%     2. Spike extraction with drift correction (AP -> NIDQ -> REC)
%     3. Isolation analysis (PC features, signal-to-noise per cluster)
%     4. Raster extraction (trial-aligned spikes for each task type)
%     5. Auto-curation (threshold-based unit classification)
%     6. Isolated unit extraction (identify well-isolated units)
%     7. Visualization (depth-sorted firing rate heatmaps)
%
%   Parameters:
%     cfg    - Configuration struct from mind_snag_config. Must have:
%                cfg.data_root       - path to experimental data
%                cfg.kilosort_venv   - path to Python KS4 virtualenv
%              See mind_snag_config for all options.
%     day    - Recording date (YYMMDD string, e.g. '250224')
%     recs   - Cell array of recording numbers (e.g. {'007','009','010'})
%     tower  - Recording setup name (e.g. 'LPPC_LPFC_modularV1')
%     np     - Neuropixel probe number (1 or 2)
%     stages - (Optional) Cell array of stage names to run. Default: all.
%              Valid: {'kilosort','extract','isolation','rasters',
%                      'curation','iso_units','heatmap'}
%
%   Example (non-grouped, full pipeline):
%     cfg = mind_snag_config('data_root', '/my/data', 'kilosort_venv', '/opt/ks4');
%     pipeline_KS4(cfg, '250224', {'007','009','010'}, 'LPPC_LPFC_modularV1', 1);
%
%   Example (run only extraction and isolation):
%     pipeline_KS4(cfg, '250224', {'007'}, 'tower', 1, {'extract','isolation'});
%
%   See also: mind_snag_config, setup, run_kilosort4, extract_spikes,
%             compute_isolation, extract_rasters, extract_isolated_units, fr_heatmap

% Validate config
assert(~isempty(cfg.data_root), 'mind_snag:config', ...
    'cfg.data_root must be set. Run: cfg = mind_snag_config(''data_root'', ''/path/to/data'')');
assert(exist(cfg.data_root, 'dir') == 7, 'mind_snag:io', ...
    'Data root not found: %s', cfg.data_root);

% Default: run all stages
all_stages = {'kilosort', 'extract', 'isolation', 'rasters', ...
              'curation', 'iso_units', 'heatmap'};
if nargin < 6 || isempty(stages)
    stages = all_stages;
end

grouped = (length(recs) > 1);

fprintf('\n=== mind_snag Pipeline KS4 ===\n');
fprintf('Day: %s | Tower: %s | NP: %d | Grouped: %d\n', day, tower, np, grouped);
fprintf('Recordings: %s\n', strjoin(recs, ', '));
fprintf('Stages: %s\n', strjoin(stages, ' -> '));
fprintf('Data root: %s\n\n', cfg.data_root);

%% Stage 1: Kilosort4 execution
if ismember('kilosort', stages)
    fprintf('--- Stage 1: Running Kilosort4 ---\n');
    run_kilosort4(cfg, day, 1, recs, tower, np, grouped);
    fprintf('--- Kilosort4 complete ---\n\n');
end

%% Stage 2: Spike extraction with drift correction
if ismember('extract', stages)
    fprintf('--- Stage 2: Extracting spikes ---\n');
    if grouped
        extract_spikes(cfg, day, recs, tower, np, 1);
    else
        for i = 1:length(recs)
            extract_spikes(cfg, day, recs{i}, tower, np, 0);
        end
    end
    fprintf('--- Spike extraction complete ---\n\n');
end

%% Stage 3: Isolation analysis
if ismember('isolation', stages)
    fprintf('--- Stage 3: Computing isolation scores ---\n');
    if grouped
        compute_isolation(cfg, day, recs, tower, np, 1);
    else
        for i = 1:length(recs)
            compute_isolation(cfg, day, recs{i}, tower, np, 0);
        end
    end
    fprintf('--- Isolation analysis complete ---\n\n');
end

%% Stage 4: Raster extraction
if ismember('rasters', stages)
    fprintf('--- Stage 4: Extracting rasters ---\n');
    if grouped
        extract_rasters(cfg, day, recs, tower, np, 1);
    else
        for i = 1:length(recs)
            extract_rasters(cfg, day, recs{i}, tower, np, 0);
        end
    end
    fprintf('--- Raster extraction complete ---\n\n');
end

%% Stage 5: Auto-curation
if ismember('curation', stages)
    fprintf('--- Stage 5: Auto-curation ---\n');
    fprintf('Note: Auto-curation currently requires the Spike_sorting_GUI_KS4_V5 app.\n');
    fprintf('Thresholds: L-Ratio=%.2f, ISI=%.2f, t-Ratio=%.2f\n', ...
        cfg.curation.l_ratio_threshold, ...
        cfg.curation.isi_violation_rate, ...
        cfg.curation.isolated_t_ratio);
    warning('mind_snag:curation', ...
        'Programmatic auto-curation not yet extracted from GUI. Skipping.');
    fprintf('--- Auto-curation skipped ---\n\n');
end

%% Stage 6: Isolated unit extraction
if ismember('iso_units', stages)
    fprintf('--- Stage 6: Extracting isolated units ---\n');
    if grouped
        extract_isolated_units(cfg, day, recs, tower, np, 1);
    else
        for i = 1:length(recs)
            extract_isolated_units(cfg, day, recs{i}, tower, np, 0);
        end
    end
    fprintf('--- Isolated unit extraction complete ---\n\n');
end

%% Stage 7: Visualization
if ismember('heatmap', stages)
    fprintf('--- Stage 7: Generating heatmaps ---\n');
    fr_heatmap(cfg, day, tower, np, grouped, recs);
    fprintf('--- Heatmaps complete ---\n\n');
end

fprintf('=== Pipeline complete ===\n');

end
