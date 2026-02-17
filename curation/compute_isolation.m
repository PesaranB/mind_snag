function compute_isolation(cfg, day, rec, tower, np, grouped, clu_id)
% COMPUTE_ISOLATION Compute PC features and isolation scores per cluster
%
%   compute_isolation(cfg, day, rec, tower, np, grouped)
%   compute_isolation(cfg, day, rec, tower, np, grouped, clu_id)
%
%   For each cluster, extracts PC features on the max-amplitude channel,
%   segments the recording into time windows, and computes isolation
%   metrics (signal-to-noise score) against nearby noise channels.
%
%   Parameters:
%     cfg     - Configuration struct from mind_snag_config
%     day     - Recording date (YYMMDD string)
%     rec     - Recording number(s), string or cell array
%     tower   - Recording setup name
%     np      - Neuropixel probe number (1 or 2)
%     grouped - 0 for individual, 1 for concatenated
%     clu_id  - (Optional) Specific cluster IDs to process (0-indexed)
%
%   Outputs:
%     Saves SortData.mat per cluster containing isolation features.
%
%   See also: extract_spikes, extract_isolated_units, mind_snag_config

data_root = cfg.data_root;
assert(~isempty(data_root), 'mind_snag:config', 'cfg.data_root must be set.');

if nargin < 7; clu_id = []; end
IsoWin = cfg.isolation.window_sec;

if cfg.ks_version == 4
    ks_name = '_KS4';
    KSsaveDir = 'KSsave_KS4';
else
    ks_name = '';
    KSsaveDir = '';
end

if grouped
    rec_name = strjoin(rec, '_');
    nR = length(rec);
    GROUPEDFLAG = 'Grouped';
else
    rec_name = rec;
    nR = 1;
    GROUPEDFLAG = 'NotGrouped';
end

folderName = fullfile(data_root, day, 'spikeglx_data', ...
    ['grouped_recordings.' tower '.' num2str(np)]);
folderRec = fullfile(folderName, ['group' rec_name ks_name]);
KS_dir = folderRec;
params.excludeNoise = false;
sp = loadKSdir(KS_dir, params);

clear max_site min_site
[max_site, min_site] = clus_channel_infor(cfg, day, rec, tower, np, grouped);

ksFile = fullfile(KS_dir, 'cluster_KSLabel.tsv');
[cids, cgs] = readClusterGroupsCSV(ksFile);
goodClus = cids(cgs == 2);

pcFeatInd = sp.pcFeatInd;

for i = 1:nR
    if nR == 1
        rec = {rec};
    end
    rec_this = rec{i};

    if grouped == 1
        NPclu_KSdir = fullfile(data_root, day, rec_this, ...
            ['rec' num2str(rec_this) '.' tower '.' num2str(np) '.' GROUPEDFLAG '.NPclu.mat']);
        NPclu_data = load(NPclu_KSdir);
        RecspikeTemps = NPclu_data.NPclu(:,2);
        RecspikeTimes = NPclu_data.NPclu(:,1);
        tempScalingAmps = NPclu_data.tempScalingAmps;
        pcFeat = NPclu_data.pcFeat;
    else
        RecspikeTemps = sp.clu;
        RecspikeTimes = sp.st;
        tempScalingAmps = sp.tempScalingAmps;
        pcFeat = sp.pcFeat;
    end

    temps = sp.temps;

    if ~isempty(clu_id)
        myClus = clu_id + 1;
    else
        myClus = cids + 1;
    end

    for iUnit = 1:length(myClus)
        myClu = myClus(iUnit);
        if grouped == 1
            myrecspikes = find(RecspikeTemps == myClu);
        else
            myrecspikes = find(RecspikeTemps == myClu - 1);
        end

        SortData = struct([]);
        if length(myrecspikes)
            myAmp = repmat(tempScalingAmps(myrecspikes), [1, 3, 1]);
            tmpInd = pcFeatInd(myClu,:) + 1;
            spikechannel_ind = max_site(myClu);

            temp_waveform_Ind = spikechannel_ind;
            if ~isempty(temp_waveform_Ind)
                mySpikeWf = sq(temps(myClu, :, temp_waveform_Ind));
            else
                mySpikeWf = NaN;
            end

            pcfeat_spike_Ind = find(tmpInd == spikechannel_ind);
            mySpiketimes = RecspikeTimes(myrecspikes);
            mypcFeat_spike = pcFeat(myrecspikes, 1:3, pcfeat_spike_Ind) .* myAmp;

            otherspikesClu = find(max_site == max_site(myClu));
            otherspikesClu(otherspikesClu == myClu) = [];
            nOtherClu = length(otherspikesClu);

            clear mypcFeat_otherspike myOtherSpikeTimes myOtherSpikeWf
            if nOtherClu
                mypcFeat_otherspike = cell(1, nOtherClu);
                myOtherSpikeTimes = cell(1, nOtherClu);
                for iOtherClu = 1:nOtherClu
                    myOtherClu = otherspikesClu(iOtherClu);
                    if grouped == 1
                        myotherspikes = find(RecspikeTemps == myOtherClu);
                    else
                        myotherspikes = find(RecspikeTemps == myOtherClu - 1);
                    end
                    tmpInd_other = pcFeatInd(myOtherClu,:) + 1;
                    otherspikechannel_ind = max_site(myOtherClu);
                    pcfeat_spike_other_Ind = find(tmpInd_other == otherspikechannel_ind);
                    myOtherAmp = repmat(tempScalingAmps(myotherspikes), [1, 3, 1]);
                    mypcFeat_otherspike{iOtherClu} = pcFeat(myotherspikes, 1:3, pcfeat_spike_other_Ind) .* myOtherAmp;
                    myOtherSpikeTimes{iOtherClu} = RecspikeTimes(myotherspikes);
                    myOthertemp_waveform_Ind = otherspikechannel_ind;
                    if ~isempty(myOthertemp_waveform_Ind)
                        myOtherSpikeWf(iOtherClu,:) = sq(temps(myOtherClu, :, myOthertemp_waveform_Ind));
                    else
                        myOtherSpikeWf(iOtherClu,:) = NaN;
                    end
                end
            else
                myOtherSpikeWf = [];
                myOtherSpikeTimes = [];
                mypcFeat_otherspike = [];
            end

            % Extract noise channel
            noise_channel_Ind = min_site(myClu);
            noiseSiteWf = sq(temps(myClu, :, noise_channel_Ind));
            pcfeat_noise_Ind = find(tmpInd == noise_channel_Ind);
            mypcFeat_noise = pcFeat(myrecspikes, 1:3, pcfeat_noise_Ind) .* myAmp;

            % Segment into time windows
            if ~isempty(RecspikeTimes)
                FracEnd = ceil(max(RecspikeTimes) / IsoWin) * IsoWin;
                Frac = round(0:IsoWin:FracEnd);
                nFrames = length(Frac) - 1;
            end

            if nFrames ~= 0
                for iFrame = 1:nFrames
                    ind = intersect(find(mySpiketimes >= Frac(iFrame)), find(mySpiketimes <= Frac(iFrame+1)));
                    SortData(iFrame).CluWf = mySpikeWf;
                    SortData(iFrame).NoiseWf = noiseSiteWf;
                    if ~isempty(ind)
                        SortData(iFrame).Noise = mypcFeat_noise(ind,:);
                        SortData(iFrame).Unit = mypcFeat_spike(ind,:);
                        SortData(iFrame).meanspikeamp = mean(mypcFeat_spike(ind,:), 1);
                        SortData(iFrame).meannoiseamp = mean(mypcFeat_noise(ind,:), 1);
                        SortData(iFrame).sdnoiseamp = std(mypcFeat_noise(ind,:), [], 1);
                        SortData(iFrame).score = abs((SortData(iFrame).meanspikeamp(1) - SortData(iFrame).meannoiseamp(1))) ./ SortData(iFrame).sdnoiseamp(1);
                        SortData(iFrame).UnitIso = 0;
                        SortData(iFrame).Clu = myClu;
                    else
                        SortData(iFrame).Noise = [];
                        SortData(iFrame).Unit = [];
                        SortData(iFrame).meanspikeamp = [];
                        SortData(iFrame).meannoiseamp = [];
                        SortData(iFrame).sdnoiseamp = [];
                        SortData(iFrame).score = [];
                        SortData(iFrame).UnitIso = 0;
                        SortData(iFrame).Clu = myClu;
                    end
                    if nOtherClu
                        Other = cell(1, nOtherClu);
                        for iOtherClu = 1:nOtherClu
                            ind_o = intersect(find(myOtherSpikeTimes{iOtherClu} >= Frac(iFrame)), ...
                                find(myOtherSpikeTimes{iOtherClu} <= Frac(iFrame+1)));
                            Other{iOtherClu} = mypcFeat_otherspike{iOtherClu}(ind_o,:);
                            SortData(iFrame).Other = Other;
                            SortData(iFrame).OtherClu = otherspikesClu;
                            GoodBad = zeros(1, length(otherspikesClu));
                            GoodBad(ismember(otherspikesClu, goodClus + 1)) = 1;
                            SortData(iFrame).OtherGoodBad = GoodBad;
                            SortData(iFrame).OtherCluWf = myOtherSpikeWf;
                        end
                    else
                        SortData(iFrame).Other = [];
                        SortData(iFrame).OtherClu = [];
                        SortData(iFrame).OtherGoodBad = [];
                        SortData(iFrame).OtherCluWf = [];
                    end
                end
            else
                SortData(1).Noise = mypcFeat_noise;
                SortData(1).Unit = mypcFeat_spike;
                SortData(1).meanspikeamp = mean(mypcFeat_spike, 1);
                SortData(1).meannoiseamp = mean(mypcFeat_noise, 1);
                SortData(1).sdnoiseamp = std(mypcFeat_noise, [], 1);
                SortData(1).score = abs((SortData(1).meanspikeamp(1) - SortData(1).meannoiseamp(1))) ./ SortData(1).sdnoiseamp(1);
                SortData(1).UnitIso = 0;
                SortData(1).Clu = myClu;
            end
        else
            SortData(1).Clu = myClu;
            SortData(1).UnitIso = 0;
            SortData(1).Unit = [];
            SortData(1).Noise = [];
            SortData(1).Other = [];
            SortData(1).OtherClu = [];
            SortData(1).CluWf = [];
            SortData(1).NoiseWf = [];
            SortData(1).OtherCluWf = [];
        end

        if grouped
            output_dir = fullfile(data_root, day, rec_this, rec_name, KSsaveDir);
        else
            output_dir = fullfile(data_root, day, rec_this, KSsaveDir);
        end
        if ~exist(output_dir, 'dir')
            mkdir(output_dir);
        end
        out_file = fullfile(output_dir, ['rec' rec_this '.' tower '.' num2str(np) '.' num2str(myClu) '.' GROUPEDFLAG '.SortData.mat']);
        save(out_file, 'SortData', '-v7.3');
        fprintf('Saved: %s\n', out_file);
    end
end

end
