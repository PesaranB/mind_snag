%% Example: Run mind_snag pipeline on a single recording
%
%  This example shows how to configure and run the full spike sorting
%  pipeline on a single Neuropixel recording.

%% 1. Setup
% Add mind_snag to the MATLAB path (run once per session)
cd('/path/to/mind_snag');
setup;

%% 2. Configure
cfg = mind_snag_config( ...
    'data_root',     '/path/to/monkey/data', ...    % where SpikeGLX data lives
    'kilosort_venv', '/path/to/kilosort/venv' ...   % Python venv with kilosort[gui]==4.0.22
);

% Optionally override defaults:
%   cfg.gpu = 0;                              % use CPU (slower)
%   cfg.curation.l_ratio_threshold = 0.3;     % relax L-ratio threshold
%   cfg.raster.time_window = [-500, 1000];    % wider raster window

%% 3. Define the recording
day   = '250224';                   % date in YYMMDD format
recs  = {'007'};                    % single recording number
tower = 'LPPC_LPFC_modularV1';     % recording setup name
np    = 1;                          % Neuropixel probe number (1 or 2)

%% 4. Run the full pipeline
pipeline_KS4(cfg, day, recs, tower, np);

% This runs all 7 stages in order:
%   1. Kilosort4 execution
%   2. Spike extraction with drift correction
%   3. Isolation analysis
%   4. Raster extraction
%   5. Auto-curation (currently skipped - requires GUI)
%   6. Isolated unit extraction
%   7. Firing rate heatmap visualization

%% 5. Run specific stages only
% If Kilosort4 has already been run, skip to extraction:
pipeline_KS4(cfg, day, recs, tower, np, {'extract', 'isolation', 'rasters'});

%% 6. Check outputs
% After the pipeline completes, outputs are at:
%   {data_root}/{day}/{rec}/rec{rec}.{tower}.{np}.NotGrouped.NPclu.mat
%   {data_root}/{day}/{rec}/KSsave_KS4/rec{rec}.{tower}.{np}.{clu}.NotGrouped.SortData.mat
%   {data_root}/{day}/{rec}/KSsave_KS4/rec{rec}.{tower}.{np}.{clu}.NotGrouped.RasterData.mat
