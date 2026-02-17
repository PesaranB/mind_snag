%% Example: Run mind_snag pipeline on grouped (concatenated) recordings
%
%  When multiple recordings are made in the same session, they can be
%  concatenated before spike sorting for better template estimation.
%  This example shows how to run the pipeline in grouped mode.

%% 1. Setup
cd('/path/to/mind_snag');
setup;

%% 2. Configure
cfg = mind_snag_config( ...
    'data_root',     '/path/to/monkey/data', ...
    'kilosort_venv', '/path/to/kilosort/venv' ...
);

%% 3. Define the session (multiple recordings)
day   = '250224';
recs  = {'007', '009', '010', '011'};   % multiple recordings to concatenate
tower = 'LPPC_LPFC_modularV1';
np    = 1;

%% 4. Run the full pipeline
% When recs has more than one entry, the pipeline automatically runs
% in grouped mode: concatenating .bin files before Kilosort4, then
% splitting spike times back per-recording using duration offsets.
pipeline_KS4(cfg, day, recs, tower, np);

%% 5. Outputs
% Grouped outputs are stored at:
%   {data_root}/{day}/spikeglx_data/grouped_recordings.{tower}.{np}/
%       group{rec1}_{rec2}_{...}_KS4/    <- Kilosort4 output
%
% Per-recording outputs (after splitting):
%   {data_root}/{day}/{rec}/{rec1}_{rec2}_{...}/KSsave_KS4/
%       rec{rec}.{tower}.{np}.{clu}.Grouped.SortData.mat
%       rec{rec}.{tower}.{np}.{clu}.Grouped.RasterData.mat
%
%   {data_root}/{day}/{rec}/
%       rec{rec}.{tower}.{np}.Grouped.NPclu.mat
