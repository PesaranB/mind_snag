function stitch_table = stitch_neurons(cfg, day, recs, tower, np, grouped, cluster_type)
% STITCH_NEURONS Cross-recording neuron identity matching
%
%   stitch_table = stitch_neurons(cfg, day, recs, tower, np, grouped, cluster_type)
%
%   Identifies the same neuron across multiple recordings by correlating
%   firing rate PSTHs and waveform shapes. For each unique channel, finds
%   clusters within a configurable electrode range and computes pairwise
%   Pearson correlations of PSTH and waveform across recordings.
%
%   Algorithm:
%     1. For each unique channel across recordings, find clusters within
%        +/- cfg.stitching.channel_range electrodes
%     2. For each cluster in each recording, compute Pearson correlation
%        of its PSTH and waveform against all clusters on same/nearby
%        channels in other recordings
%     3. If both FR correlation >= threshold AND waveform correlation >=
%        threshold, stitch (same neuron)
%     4. Deduplicate and filter by minimum recording count
%
%   Parameters:
%     cfg          - Configuration struct from mind_snag_config
%                    Uses: cfg.stitching.fr_corr_threshold  (default 0.85)
%                          cfg.stitching.wf_corr_threshold  (default 0.85)
%                          cfg.stitching.min_recordings     (default 2)
%                          cfg.stitching.channel_range      (default 10)
%     day          - Recording date (YYMMDD string)
%     recs         - Cell array of recording numbers (e.g. {'007','009','010'})
%     tower        - Recording setup name
%     np           - Neuropixel probe number (1 or 2)
%     grouped      - 0 for individual, 1 for concatenated
%     cluster_type - 'All', 'Good', or 'Isolated' (which clusters to stitch)
%
%   Returns:
%     stitch_table - [N x numRecs] matrix where each row is a stitched neuron.
%                    Columns correspond to recs. Values are cluster IDs.
%                    NaN means the neuron was not found in that recording.
%
%   Example:
%     cfg = mind_snag_config('data_root', '/path/to/data');
%     stitch = stitch_neurons(cfg, '250224', {'007','009','010'}, ...
%         'LPPC_LPFC_modularV1', 1, 0, 'Isolated');
%
%   See also: mind_snag_config, extract_spikes, compute_isolation

data_root = cfg.data_root;
assert(~isempty(data_root), 'mind_snag:config', 'cfg.data_root must be set.');

fr_threshold = cfg.stitching.fr_corr_threshold;
wf_threshold = cfg.stitching.wf_corr_threshold;
min_recs     = cfg.stitching.min_recordings;
chan_range    = cfg.stitching.channel_range;

if grouped
    Groupflag = 'Grouped';
    grouped_rec_name = strjoin(recs, '_');
else
    Groupflag = 'NotGrouped';
    grouped_rec_name = recs{1};
end

numRecs = length(recs);
bn = [-300 500];

%% Load cluster info for each recording
fprintf('Loading cluster info for %d recordings...\n', numRecs);

cluIDs = cell(1, numRecs);
tmpIsoCluInfor = cell(1, numRecs);
chan_map = [];

for iR = 1:numRecs
    rec = recs{iR};
    Npfilepath = fullfile(data_root, day, rec, ...
        ['rec' rec '.' tower '.' num2str(np) '.' Groupflag '.NPclu.mat']);
    assert(exist(Npfilepath, 'file') == 2, 'mind_snag:io', ...
        'NPclu file not found: %s\nRun extract_spikes first.', Npfilepath);

    Npfile = load(Npfilepath);
    cluIDs{iR} = Npfile.Clu_info;

    if strcmp(cluster_type, 'All')
        tmpIsoCluInfor{iR} = Npfile.Clu_info;
        tmpIsoChannel_Indexs = Npfile.Clu_info(:,2);
    elseif strcmp(cluster_type, 'Good')
        tmpIsoCluInfor{iR} = Npfile.KSclu_info;
        tmpIsoChannel_Indexs = Npfile.KSclu_info(:,2);
    elseif strcmp(cluster_type, 'Isolated')
        assert(isfield(Npfile, 'IsoClu_info'), 'mind_snag:data', ...
            'IsoClu_info not found. Run extract_isolated_units first.');
        tmpIsoCluInfor{iR} = Npfile.IsoClu_info;
        tmpIsoChannel_Indexs = Npfile.IsoClu_info(:,2);
    else
        error('mind_snag:arg', 'cluster_type must be ''All'', ''Good'', or ''Isolated''');
    end

    % Load channel map from KS directory
    if isempty(chan_map)
        folderName = fullfile(data_root, day, 'spikeglx_data', ...
            ['grouped_recordings.' tower '.' num2str(np)]);
        if grouped
            folderRec = fullfile(folderName, ['group' grouped_rec_name '_KS4']);
        else
            folderRec = fullfile(folderName, ['group' recs{1} '_KS4']);
        end
        params.excludeNoise = false;
        sp = loadKSdir(folderRec, params);
        chan_map = sp.chan_map + 1;  % 0->1 indexing
    end

    IsoChans_iR = chan_map(tmpIsoChannel_Indexs);
    if iR == 1
        allIsoChans = IsoChans_iR;
    else
        allIsoChans = cat(1, allIsoChans, IsoChans_iR);
    end
end

uniChans = unique(allIsoChans);
fprintf('Found %d unique channels across recordings.\n', length(uniChans));

%% Helper: get cluster IDs for a given channel across recordings
    function clusterIDs = getClusterID(channelID)
        ChannelID_ind = find(chan_map == channelID);
        clusterIDs = cell(1, numRecs);
        for ii = 1:numRecs
            tmpCluId = tmpIsoCluInfor{ii};
            thisRecCluId = tmpCluId(:,1);
            thisRecChanId = tmpCluId(:,2);
            if ~isempty(ChannelID_ind)
                cluster_Ind = find(thisRecChanId == ChannelID_ind);
                if ~isempty(cluster_Ind)
                    clusterIDs{ii} = thisRecCluId(cluster_Ind);
                else
                    clusterIDs{ii} = [];
                end
            else
                clusterIDs{ii} = [];
            end
        end
    end

%% Helper: get channels within range
    function channel_IDS = getWithinRangeChannels(selected_channel)
        NPelec = getNP_chanDepthInfo(day, recs{1}, np, tower, data_root);
        corresponding_elecNum = NPelec.elecNum(selected_channel);
        elecNum_range = corresponding_elecNum + (-chan_range:chan_range);
        channel_indexs = find(ismember(NPelec.elecNum, elecNum_range));
        channel_IDS = cell(1, length(channel_indexs));
        for idx = 1:length(channel_indexs)
            channel_IDS{idx} = num2str(channel_indexs(idx));
        end
    end

%% Helper: get waveform for a cluster
    function Wf = getWaveform(myClu, thisRec)
        if grouped
            SortDatapath = fullfile(data_root, day, thisRec, grouped_rec_name, ...
                'KSsave_KS4', ['rec' thisRec '.' tower '.' num2str(np) '.' ...
                num2str(myClu) '.' Groupflag '.SortData.mat']);
        else
            SortDatapath = fullfile(data_root, day, thisRec, ...
                'KSsave_KS4', ['rec' thisRec '.' tower '.' num2str(np) '.' ...
                num2str(myClu) '.' Groupflag '.SortData.mat']);
        end
        if exist(SortDatapath, 'file')
            XX = load(SortDatapath);
            Wf = XX.SortData(1).CluWf;
        else
            Wf = nan(1, 61);
        end
    end

%% Helper: get firing rate (PSTH) for a cluster
    function rate = getFiringRate(myClu, thisRec)
        if grouped
            filename = fullfile(data_root, day, thisRec, grouped_rec_name, ...
                'KSsave_KS4', ['rec' thisRec '.' tower '.' num2str(np) '.' ...
                num2str(myClu) '.' Groupflag '.RasterData.mat']);
        else
            filename = fullfile(data_root, day, thisRec, ...
                'KSsave_KS4', ['rec' thisRec '.' tower '.' num2str(np) '.' ...
                num2str(myClu) '.' Groupflag '.RasterData.mat']);
        end
        if exist(filename, 'file')
            RD = load(filename);
            [~, sort_sp] = sortKSSpX(RD.RasterData.RT, RD.RasterData.SpikeClu);
            [rate, ~] = psth(sort_sp, bn, 10, 80, [], 0);
        else
            rate = nan(1, diff(bn) + 1);
        end
    end

%% Run stitching prediction
fprintf('Running stitching prediction...\n');
Stitch_Prediction_List = [];

for iUni_Chan = 1:length(uniChans)
    currentChan = uniChans(iUni_Chan);
    channel_IDS = getWithinRangeChannels(currentChan);

    % Gather all cluster IDs, waveforms, and rates per recording for nearby channels
    AllClusterIDs = cell(1, numRecs);
    AllWfs = cell(1, numRecs);
    AllRates = cell(1, numRecs);

    for irec = 1:numRecs
        thisRec_ClusterIDs = [];
        thisRec_Wfs = [];
        thisRec_Rates = [];

        for iChan = 1:length(channel_IDS)
            thisChan = channel_IDS{iChan};
            ChannelID_ind = find(chan_map == str2double(thisChan));
            if isempty(ChannelID_ind)
                continue;
            end

            currentClusterID = getClusterID(str2double(thisChan));
            Chan_ClusterIDs = currentClusterID{irec};
            if isempty(Chan_ClusterIDs)
                continue;
            end

            thisRec_ClusterIDs = [thisRec_ClusterIDs; Chan_ClusterIDs];

            % Get waveforms and rates for each cluster
            for ic = 1:length(Chan_ClusterIDs)
                clu = Chan_ClusterIDs(ic);
                wf = getWaveform(clu, recs{irec});
                fr = getFiringRate(clu, recs{irec});
                thisRec_Wfs = [thisRec_Wfs; wf];
                thisRec_Rates = [thisRec_Rates; fr];
            end
        end

        AllClusterIDs{irec} = thisRec_ClusterIDs;
        AllWfs{irec} = thisRec_Wfs;
        AllRates{irec} = thisRec_Rates;
    end

    % For each cluster on the current channel, compare to other recordings
    currentClusterID_thisChan = getClusterID(currentChan);

    for irec = 1:numRecs
        thisRec_Clus = currentClusterID_thisChan{irec};
        if isempty(thisRec_Clus)
            continue;
        end

        for iclus = 1:length(thisRec_Clus)
            thiscluster_ID = thisRec_Clus(iclus);
            FR = getFiringRate(thiscluster_ID, recs{irec});
            Wf = getWaveform(thiscluster_ID, recs{irec});

            Stitched_List_PerUnit = nan(1, numRecs);
            Stitched_List_PerUnit(irec) = thiscluster_ID;

            OtherRec_Indexes = find(~ismember(1:numRecs, irec));

            for iotherrec = 1:length(OtherRec_Indexes)
                thisotherRec_ind = OtherRec_Indexes(iotherrec);
                otherRec_Clus_IDs = AllClusterIDs{thisotherRec_ind};

                if isempty(otherRec_Clus_IDs)
                    continue;
                end

                comparedOtherWfs = AllWfs{thisotherRec_ind};
                ComparedOtherRates = AllRates{thisotherRec_ind};

                comparedWfs = [Wf; comparedOtherWfs];
                ComparedRates = [FR; ComparedOtherRates];

                FR_correlate = corrcoef(ComparedRates', 'Rows', 'pairwise');
                FR_correlate = FR_correlate(1, 2:end);

                Wf_correlate = corrcoef(comparedWfs', 'Rows', 'pairwise');
                Wf_correlate = Wf_correlate(1, 2:end);

                FR_correlate(isnan(FR_correlate)) = -Inf;
                [sortedFR_corr, idx_FR_corr] = sort(FR_correlate, 'descend');
                maxFRIdx = idx_FR_corr(1);

                if sortedFR_corr(1) >= fr_threshold && Wf_correlate(maxFRIdx) >= wf_threshold
                    otherRec_cluster_ID = otherRec_Clus_IDs(maxFRIdx);
                    Stitched_List_PerUnit(thisotherRec_ind) = otherRec_cluster_ID;
                end
            end

            Stitch_Prediction_List = [Stitch_Prediction_List; Stitched_List_PerUnit];
        end
    end
end

%% Deduplicate and filter
if isempty(Stitch_Prediction_List)
    stitch_table = [];
    fprintf('No stitched neurons found.\n');
    return;
end

nanMask = isnan(Stitch_Prediction_List);
List_equalNaN = Stitch_Prediction_List;
List_equalNaN(nanMask) = 0;
[~, ia] = unique(List_equalNaN, 'rows');
UniqueStitch_List = Stitch_Prediction_List(ia, :);

% Filter by minimum recording count
rowsWithMultiple = find(sum(~isnan(UniqueStitch_List), 2) >= min_recs);
stitch_table = UniqueStitch_List(rowsWithMultiple, :);

fprintf('Stitching complete: %d neurons found across %d recordings.\n', ...
    size(stitch_table, 1), numRecs);

end
