function stitch_table = Auto_Stitching_V2(cfg, day, recs, tower, np, grouped, cluster_type, output_dir)
% AUTO_STITCHING_V2 Cross-recording neuron identity matching
%
%   stitch_table = Auto_Stitching_V2(cfg, day, recs, tower, np, grouped, cluster_type)
%   stitch_table = Auto_Stitching_V2(cfg, day, recs, tower, np, grouped, cluster_type, output_dir)
%
%   Identifies the same neuron across multiple recordings by correlating
%   firing rate PSTHs and waveform shapes. Optionally saves results in
%   the NPSpike_KS4_Database format.
%
%   Parameters:
%     cfg          - Configuration struct from mind_snag_config
%     day          - Recording date (YYMMDD string)
%     recs         - Cell array of recording numbers (e.g. {'007','009','010'})
%     tower        - Recording setup name
%     np           - Neuropixel probe number (1 or 2)
%     grouped      - 0 for individual, 1 for concatenated
%     cluster_type - 'All', 'Good', or 'Isolated'
%     output_dir   - (Optional) Directory to save database file. If empty,
%                    saves to data_root/day/stitching_results/
%
%   Returns:
%     stitch_table - [N x numRecs] matrix. Each row is a stitched neuron.
%                    Columns correspond to recs. Values are cluster IDs.
%                    NaN means neuron not found in that recording.
%
%   Example:
%     cfg = mind_snag_config('data_root', '/path/to/data');
%     stitch = Auto_Stitching_V2(cfg, '250224', {'007','009','010'}, ...
%         'LPPC_LPFC_modularV1', 1, 0, 'Isolated');
%
%   See also: stitch_neurons, save_stitch_results, mind_snag_config

% Run stitching
stitch_table = stitch_neurons(cfg, day, recs, tower, np, grouped, cluster_type);

% Save results
if ~isempty(stitch_table)
    if nargin < 8 || isempty(output_dir)
        output_dir = fullfile(cfg.data_root, day, 'stitching_results');
    end
    save_stitch_results(cfg, stitch_table, day, recs, tower, np, output_dir);
end

end
