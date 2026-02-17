function [max_site, min_site] = clus_channel_infor(cfg, day, rec, tower, np, grouped)
% CLUS_CHANNEL_INFOR Get best and worst channel for each cluster
%
%   [max_site, min_site] = clus_channel_infor(cfg, day, rec, tower, np, grouped)
%
%   For each cluster, determines the channel with highest waveform energy
%   (max_site) and lowest energy (min_site), weighted by PC feature coverage.
%
%   Parameters:
%     cfg     - Configuration struct from mind_snag_config
%     day     - Recording date (YYMMDD string)
%     rec     - Recording number(s)
%     tower   - Recording setup name
%     np      - Probe number
%     grouped - 0 or 1

data_root = cfg.data_root;
KSversionflag = (cfg.ks_version == 4);

if KSversionflag
    ks_name = '_KS4';
else
    ks_name = '';
end

folderName = fullfile(data_root, day, 'spikeglx_data', ...
    ['grouped_recordings.' tower '.' num2str(np)]);
if grouped
    rec_name = strjoin(rec, '_');
    folderRec = fullfile(folderName, ['group' rec_name ks_name]);
else
    folderRec = fullfile(folderName, ['group' rec ks_name]);
end

KS_dir = folderRec;
params.excludeNoise = false;
sp = loadKSdir(KS_dir, params);

pcFeatInd = sp.pcFeatInd;
spikeTemps = sp.clu;
temps = sp.temps;
ksFile = fullfile(KS_dir, 'cluster_KSLabel.tsv');
[cids, ~] = readClusterGroupsCSV(ksFile);
myClus = cids + 1;

max_site = [];
min_site = [];

alpha = 1;
min_pc_threshold = 0.1;

for iUnit = 1:length(myClus)
    myClu = myClus(iUnit);
    myspikes = find(spikeTemps == myClu - 1);
    if length(myspikes)
        thisCluTemp = sq(temps(myClu,:,:));
        tmpInd = pcFeatInd(myClu,:) + 1;
        thisCluWfs = thisCluTemp(:, tmpInd);
        ptp_energy = sum(thisCluWfs.^2, 1);

        mypcfeat = sp.pcFeat(myspikes, 1:3, :);
        nonZerosPCRatios = zeros(1, 10);
        for ch = 1:10
            pc_ch = squeeze(mypcfeat(:, :, ch));
            zero_mask = all(pc_ch == 0, 2);
            nonZerosPCRatios(ch) = 1 - sum(zero_mask) / size(pc_ch, 1);
        end

        ptp_norm = ptp_energy / max(ptp_energy);
        nzr_norm = nonZerosPCRatios / max(nonZerosPCRatios);

        combinedScore = alpha * ptp_norm + (1 - alpha) * nzr_norm;
        [~, bestChannelInd] = max(combinedScore);

        if nonZerosPCRatios(bestChannelInd) < 0.5
            eligible = find(nonZerosPCRatios >= 0.5);
            if ~isempty(eligible)
                [~, idx] = max(combinedScore(eligible));
                bestChannelInd = eligible(idx);
            end
        end

        max_site = [max_site; tmpInd(bestChannelInd)];

        [~, minEnergyInd] = min(ptp_energy);
        if nonZerosPCRatios(minEnergyInd) < min_pc_threshold
            eligible = find(nonZerosPCRatios >= min_pc_threshold & ptp_energy > 0);
            if ~isempty(eligible)
                [~, idx] = min(ptp_energy(eligible));
                minEnergyInd = eligible(idx);
            end
        end
        min_site = [min_site; tmpInd(minEnergyInd)];
    end
end

end
