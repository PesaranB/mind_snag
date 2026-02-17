%% Example: Cross-recording neuron identity matching (stitching)
%
%  After spike sorting multiple recordings, this identifies the same
%  neuron across recordings by correlating firing rate PSTHs and
%  waveform shapes.

%% 1. Setup
cd('/path/to/mind_snag');
setup;

%% 2. Configure
cfg = mind_snag_config( ...
    'data_root', '/path/to/monkey/data' ...
);

% Stitching-specific settings (these are the defaults):
%   cfg.stitching.fr_corr_threshold = 0.85;   % PSTH correlation threshold
%   cfg.stitching.wf_corr_threshold = 0.85;   % waveform correlation threshold
%   cfg.stitching.min_recordings    = 2;       % minimum recordings a neuron must appear in
%   cfg.stitching.channel_range     = 10;      % electrode range for neighbor search

%% 3. Define the session
day   = '250224';
recs  = {'007', '009', '010'};
tower = 'LPPC_LPFC_modularV1';
np    = 1;

%% 4. Run stitching on isolated units
% Prerequisites: pipeline stages 1-6 must have been run for each recording
% (at minimum: kilosort, extract, isolation, rasters, iso_units)

stitch_table = stitch_neurons(cfg, day, recs, tower, np, 0, 'Isolated');

% stitch_table is [N x 3] where:
%   - Each row is one neuron tracked across recordings
%   - Column j corresponds to recs{j}
%   - Values are cluster IDs; NaN means not found in that recording

%% 5. Inspect results
fprintf('Found %d neurons across %d recordings:\n', size(stitch_table, 1), length(recs));
for i = 1:size(stitch_table, 1)
    fprintf('  Neuron %d: ', i);
    for j = 1:length(recs)
        if isnan(stitch_table(i, j))
            fprintf('rec%s=--  ', recs{j});
        else
            fprintf('rec%s=clu%d  ', recs{j}, stitch_table(i, j));
        end
    end
    fprintf('\n');
end

%% 6. Save results in NPSpike_KS4_Database format
output_dir = fullfile(cfg.data_root, day, 'stitching_results');
save_stitch_results(cfg, stitch_table, day, recs, tower, np, output_dir);

%% 7. Or use the wrapper function that does both
stitch_table = Auto_Stitching_V2(cfg, day, recs, tower, np, 0, 'Isolated');

%% 8. Stitch with different cluster types
% 'All'      - all clusters (including noise/MUA)
% 'Good'     - Kilosort-labeled good units only
% 'Isolated' - units that passed isolation analysis (recommended)
stitch_all  = stitch_neurons(cfg, day, recs, tower, np, 0, 'All');
stitch_good = stitch_neurons(cfg, day, recs, tower, np, 0, 'Good');
