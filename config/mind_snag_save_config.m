function mind_snag_save_config(cfg, filepath)
% MIND_SNAG_SAVE_CONFIG Save a mind_snag configuration to a .mat file
%
%   mind_snag_save_config(cfg, filepath)
%
%   Parameters:
%     cfg      - Configuration struct from mind_snag_config
%     filepath - Path to save the .mat file (e.g. 'my_config.mat')
%
%   Example:
%     cfg = mind_snag_config('data_root', '/my/data');
%     mind_snag_save_config(cfg, 'my_experiment_config.mat');
%
%   See also: mind_snag_config

save(filepath, 'cfg', '-v7.3');
fprintf('Configuration saved to: %s\n', filepath);

end
