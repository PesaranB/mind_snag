function fr_heatmap(cfg, day, tower, np, grouped, rec)
% FR_HEATMAP Generate depth-sorted firing rate heatmaps
%
%   fr_heatmap(cfg, day, tower, np, grouped, rec)
%
%   Parameters:
%     cfg     - Configuration struct from mind_snag_config
%     day     - Recording date (YYMMDD string)
%     tower   - Recording setup name
%     np      - Probe number
%     grouped - 0 for individual, 1 for concatenated
%     rec     - (Optional) Cell array of recording numbers

data_root = cfg.data_root;

recordings_excel_file = fullfile(data_root, 'excel', 'valid_recordings.xlsx');
data = readtable(recordings_excel_file);

if nargin < 6 || isempty(rec)
    validBehavRecs = data.Rec(strcmp(data.Day, day));
elseif iscell(rec)
    validBehavRecs = rec;
else
    rec = {rec};
    validBehavRecs = rec;
end

nR = length(validBehavRecs);

figure;
for iR = 1:nR
    rec_this = validBehavRecs{iR};
    if grouped
        GROUPEDFLAG = 'Grouped';
        rec_name = strjoin(rec, '_');
    else
        GROUPEDFLAG = 'NotGrouped';
        rec_name = rec_this;
    end

    NPclu_filename = fullfile(data_root, day, rec_this, ...
        ['rec' rec_this '.' tower '.' num2str(np) '.' GROUPEDFLAG '.NPclu.mat']);
    folderName = fullfile(data_root, day, 'spikeglx_data', ...
        ['grouped_recordings.' tower '.' num2str(np)]);
    KS_dir = fullfile(folderName, ['group' rec_name '_KS4']);
    ksFile = fullfile(KS_dir, 'cluster_KSLabel.tsv');
    [cids, ~] = readClusterGroupsCSV(ksFile);

    XX = load(NPclu_filename);
    chIds = XX.Clu_info(:, 2);

    clear NPelec
    NPelec = getNP_chanDepthInfo(day, rec_this, np, tower, data_root);
    ChanId_probe = [NPelec.ChanId];
    depth = [NPelec.depth];
    myClus = cids + 1;

    numClusters = length(myClus);
    bn = [-300 500];
    tVal = -300:500;
    numTimeBins = length(tVal);
    PSTH = zeros(numClusters, numTimeBins);

    for iUnit = 1:numClusters
        myClu = myClus(iUnit);
        if grouped
            RasterDatafile = fullfile(data_root, day, rec_this, rec_name, ...
                'KSsave_KS4', ['rec' rec_this '.' tower '.' num2str(np) '.' ...
                num2str(myClu) '.' GROUPEDFLAG '.RasterData.mat']);
        else
            RasterDatafile = fullfile(data_root, day, rec_name, ...
                'KSsave_KS4', ['rec' rec_this '.' tower '.' num2str(np) '.' ...
                num2str(myClu) '.' GROUPEDFLAG '.RasterData.mat']);
        end
        load(RasterDatafile);
        [~, Sort_sp] = sortKSSpX(RasterData.RT, RasterData.SpikeClu);
        SpikeCell = Sort_sp;
        [FR, ~] = psth(SpikeCell, bn, 10, 80, [], 0);
        FR = movmedian(FR, 3);
        FR_Sub = FR - min(FR);
        RangeFR = max(FR_Sub) - min(FR_Sub);
        rate = FR_Sub / RangeFR;
        PSTH(iUnit, :) = rate ./ max(abs(rate));
    end

    PSTH = PSTH ./ max(PSTH(:));
    PSTH = imgaussfilt(PSTH, [eps, 4]);

    Clus_Depth = [];
    for ii = 1:length(chIds)
        thisChId = chIds(ii);
        tmpInd = find(ChanId_probe == thisChId);
        thisDepth = depth(tmpInd);
        Clus_Depth = cat(1, Clus_Depth, thisDepth);
    end

    [~, sortIdx] = sort(Clus_Depth, 'ascend');

    subplot(1, nR, iR);
    sorted_PSTH = PSTH(sortIdx, :);
    sorted_PSTH(isnan(sorted_PSTH)) = 0;
    imagesc(tVal, myClus, sorted_PSTH);
    colormap(flipud(crameri('roma', 256)));
    xlabel('Time (ms)');
    ylabel('Probe Depth');
    set(gca, 'YTick', []);
    set(gca, 'YTickLabel', []);
    title(sprintf('Firing Rate - Rec: %s', rec_this));
    set(gca, 'YDir', 'normal');
end

sgtitle(sprintf('Day %s NP%d', day, np));

end
