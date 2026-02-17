function save_stitch_results(cfg, stitch_table, day, recs, tower, np, output_dir)
% SAVE_STITCH_RESULTS Save neuron stitching results to a MATLAB script file
%
%   save_stitch_results(cfg, stitch_table, day, recs, tower, np, output_dir)
%
%   Saves the stitching results in the NPSpike_KS4_Database format used
%   by the lab's analysis pipeline. Each stitched neuron becomes a line
%   in a .m script that populates a Session cell array.
%
%   Parameters:
%     cfg         - Configuration struct from mind_snag_config
%     stitch_table - [N x numRecs] matrix from stitch_neurons
%     day         - Recording date (YYMMDD string)
%     recs        - Cell array of recording numbers
%     tower       - Recording setup name
%     np          - Probe number
%     output_dir  - Directory to save the database file
%
%   See also: stitch_neurons

data_root = cfg.data_root;

if ~exist(output_dir, 'dir')
    mkdir(output_dir);
end

grouped_rec_name = strjoin(recs, '_');
base_filename = 'NPSpike_KS4_Database_';
fileName = fullfile(output_dir, sprintf('%s%s_%s.m', base_filename, day, grouped_rec_name));

if cfg.ks_version == 4
    Groupflag_str = 'Grouped';
else
    Groupflag_str = 'NotGrouped';
end

% Load channel map
folderName = fullfile(data_root, day, 'spikeglx_data', ...
    ['grouped_recordings.' tower '.' num2str(np)]);
folderRec = fullfile(folderName, ['group' grouped_rec_name '_KS4']);
params.excludeNoise = false;
sp = loadKSdir(folderRec, params);
chan_map = sp.chan_map + 1;

% Write the file
fileID = fopen(fileName, 'w');
functionHeader = sprintf('function Session = NPSpike_KS4_Database_%s_%s\n', day, grouped_rec_name);
fprintf(fileID, functionHeader);
fprintf(fileID, 'Session = cell(0, 0); ind = 1;\n\n');

for i = 1:size(stitch_table, 1)
    row = stitch_table(i,:);
    validIdx = ~isnan(row);
    allRecsIDs = recs(validIdx);
    allRecsIDsStr = strjoin(allRecsIDs, ''', ''');

    clusterIDs = row(validIdx);
    ClusterIDsStr = strtrim(sprintf('%d ', clusterIDs));

    % Get channel for each cluster
    channelStr = '';
    for iclu = 1:length(clusterIDs)
        thisClu = clusterIDs(iclu);
        thisrec = allRecsIDs{iclu};

        % Load NPclu to get channel info
        Npfilepath = fullfile(data_root, day, thisrec, ...
            ['rec' thisrec '.' tower '.' num2str(np) '.' Groupflag_str '.NPclu.mat']);
        if exist(Npfilepath, 'file')
            Npfile = load(Npfilepath, 'Clu_info');
            clu_idx = find(Npfile.Clu_info(:,1) == thisClu);
            if ~isempty(clu_idx)
                chan_idx = Npfile.Clu_info(clu_idx, 2);
                Ch = chan_map(chan_idx);
            else
                Ch = 0;
            end
        else
            Ch = 0;
        end
        channelStr = sprintf('%s%d ', channelStr, Ch);
    end
    ChannelIDsStr = strtrim(channelStr);

    fprintf(fileID, "Session{ind} = {'%s', {'%s'}, {'%s'}, %d, [%s],[%s], ind, '%s', '%s'}; ind = ind+1;\n", ...
        day, allRecsIDsStr, tower, np, ChannelIDsStr, ClusterIDsStr, data_root, 'NPSpike');
end

fclose(fileID);
fprintf('Stitch results saved to: %s\n', fileName);

end
