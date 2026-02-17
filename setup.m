function setup()
% SETUP Add mind_snag package directories to the MATLAB path
%
%   Run this once per MATLAB session before using the pipeline.
%
%   Usage:
%     cd /path/to/mind_snag
%     setup
%
%   This adds the following directories to the path:
%     sorting/      - Kilosort execution and spike extraction
%     curation/     - Auto-curation logic and isolation analysis
%     analysis/     - Raster extraction, trial alignment
%     stitching/    - Cross-session neuron stitching
%     visualization/ - Firing rate heatmaps, raster plots
%     utils/        - Shared utilities (loadKSdir, psth, etc.)
%     config/       - Configuration functions
%
%   See also: mind_snag_config

pkg_root = fileparts(mfilename('fullpath'));

dirs = {'sorting', 'curation', 'analysis', 'stitching', ...
        'visualization', 'utils', 'config', 'examples'};

for i = 1:length(dirs)
    d = fullfile(pkg_root, dirs{i});
    if exist(d, 'dir')
        addpath(genpath(d));
    end
end

addpath(pkg_root);

fprintf('mind_snag v1.0.0 loaded. %d directories added to path.\n', length(dirs) + 1);
fprintf('Next: cfg = mind_snag_config(''data_root'', ''/path/to/data'', ...) to configure.\n');

end
