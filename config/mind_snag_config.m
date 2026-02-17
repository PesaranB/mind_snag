function cfg = mind_snag_config(varargin)
% MIND_SNAG_CONFIG Create or load configuration for the mind_snag pipeline
%
%   cfg = mind_snag_config()
%       Returns a default configuration struct with placeholder paths.
%       You MUST edit the paths to match your system before running the pipeline.
%
%   cfg = mind_snag_config('param', value, ...)
%       Override specific fields. Example:
%           cfg = mind_snag_config('data_root', '/my/data', 'kilosort_venv', '/opt/ks4');
%
%   cfg = mind_snag_config(config_file)
%       Load configuration from a .mat file saved with mind_snag_save_config.
%
%   Configuration fields:
%     data_root       - Root directory for experimental data (replaces MONKEYDIR)
%     output_root     - Root directory for pipeline outputs (defaults to data_root)
%     kilosort_venv   - Path to Python virtualenv with kilosort[gui]==4.0.22
%     kilosort_script - Path to Run_kilosort4.py (included in this package)
%     probe_file      - Path to .prb channel map file
%     ks_params_dir   - Directory containing Kilosort parameter files
%     gpu             - GPU device index for Kilosort (default: 1)
%     n_threads       - Number of OpenBLAS threads (default: 64)
%
%   See also: mind_snag_save_config, setup

% Handle loading from file
if nargin == 1 && ischar(varargin{1}) && endsWith(varargin{1}, '.mat')
    loaded = load(varargin{1}, 'cfg');
    cfg = loaded.cfg;
    return;
end

% Default configuration
cfg = struct();

% --- Paths (MUST be set by user) ---
cfg.data_root       = '';   % e.g. '/vol/brains/bd1/pesaranlab/Troopa_Thalamus_Ephys_Behave1'
cfg.output_root     = '';   % defaults to data_root if empty
cfg.kilosort_venv   = '';   % e.g. '/home/user/kilosort'

% --- Kilosort settings ---
pkg_root = fileparts(fileparts(mfilename('fullpath')));
cfg.kilosort_script = fullfile(pkg_root, 'sorting', 'Run_kilosort4.py');
cfg.probe_file      = fullfile(pkg_root, 'config', 'neuropixPhase3B2_kilosortChanMap.prb');
cfg.ks_params_dir   = fullfile(pkg_root, 'config');
cfg.gpu             = 1;
cfg.n_threads       = 64;

% --- Spike sorting defaults ---
cfg.ks_version      = 4;       % Kilosort version (4 or 2.5)

% --- Auto-curation thresholds ---
cfg.curation.l_ratio_threshold   = 0.2;
cfg.curation.isi_violation_rate  = 0.2;
cfg.curation.isolated_t_ratio    = 0.6;

% --- Stitching defaults ---
cfg.stitching.fr_corr_threshold  = 0.85;
cfg.stitching.wf_corr_threshold  = 0.85;
cfg.stitching.min_recordings     = 2;
cfg.stitching.channel_range      = 10;   % electrode range for neighbor search

% --- Raster / PSTH defaults ---
cfg.raster.time_window           = [-300, 500];  % ms
cfg.raster.smoothing             = 10;           % ms gaussian std for PSTH

% --- Isolation analysis ---
cfg.isolation.window_sec         = 100;  % seconds per time window

% Apply user overrides
for i = 1:2:length(varargin)
    key = varargin{i};
    val = varargin{i+1};
    if contains(key, '.')
        % Support nested fields like 'curation.l_ratio_threshold'
        parts = strsplit(key, '.');
        cfg.(parts{1}).(parts{2}) = val;
    else
        cfg.(key) = val;
    end
end

% Default output_root to data_root
if isempty(cfg.output_root)
    cfg.output_root = cfg.data_root;
end

end
