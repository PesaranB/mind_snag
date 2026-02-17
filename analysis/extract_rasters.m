function extract_rasters(cfg, day, rec, tower, np, grouped, clu_id)
% EXTRACT_RASTERS Align spikes to behavioral trial events
%
%   extract_rasters(cfg, day, rec, tower, np, grouped)
%   extract_rasters(cfg, day, rec, tower, np, grouped, clu_id)
%
%   For each cluster, aligns spikes to trial events across task types
%   (delayed saccade, luminance selection, reach, etc.) and saves
%   trial-aligned raster data.
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
%     Saves RasterData.mat per cluster containing:
%       RasterData.Clu          - Cluster ID
%       RasterData.SpikeClu     - Trial-aligned spike times
%       RasterData.OtherClu     - Neighboring cluster IDs
%       RasterData.OtherSpikeClu - Neighboring cluster spike times
%       RasterData.RT           - Reaction times
%
%   See also: extract_spikes, compute_isolation

data_root = cfg.data_root;
if nargin < 7; clu_id = []; end

KSversionflag = (cfg.ks_version == 4);

if cfg.ks_version == 4
    ks_name = '_KS4';
else
    ks_name = '';
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

[max_site, ~] = clus_channel_infor(cfg, day, rec, tower, np, grouped);

for i = 1:nR
    if nR == 1
        rec = {rec};
    end
    rec_this = rec{i};

    folderName = fullfile(data_root, day, 'spikeglx_data', ...
        ['grouped_recordings.' tower '.' num2str(np)]);
    folderRec = fullfile(folderName, ['group' rec_name ks_name]);
    KS_dir = folderRec;
    params.excludeNoise = false;
    sp = loadKSdir(KS_dir, params);
    ksFile = fullfile(KS_dir, 'cluster_KSLabel.tsv');

    if grouped == 1
        NPclu_KSdir = fullfile(data_root, day, rec_this, ...
            ['rec' rec_this '.' tower '.' num2str(np) '.' GROUPEDFLAG '.NPclu.mat']);
        NPclu_data = load(NPclu_KSdir);
        spikeTemps = NPclu_data.NPclu(:,2);
    else
        spikeTemps = sp.clu;
    end

    [cids, ~] = readClusterGroupsCSV(ksFile);

    if ~isempty(clu_id)
        myClus = clu_id + 1;
    else
        myClus = cids + 1;
    end

    Trials = loadTrials(day, rec_this, data_root);
    if isfield(Trials, 'PyTaskType')
        trialType = {Trials.PyTaskType};
        CO_Trials = Trials(ismember(trialType, 'delayed_saccade'));
        Lum_Trials = Trials(ismember(trialType, 'luminance_reward_selection'));
        Reach_Trials = [Trials(ismember(trialType, 'delayed_reach_and_saccade')), ...
            Trials(ismember(trialType, 'delayed_reach')), ...
            Trials(ismember(trialType, 'gaze_anchoring'))];
        GAF_Trials = Trials(ismember(trialType, 'gaze_anchoring_fast'));
        Touch_feed_Trials = Trials(ismember(trialType, 'simple_touch_task_feedback'));
        Touch_Trials = Trials(ismember(trialType, 'simple_touch_task'));
        Saccade_trials = Trials(ismember(trialType, 'doublestep_saccade_fast'));
        Null_Trials = Trials(ismember(trialType, 'null'));
    else
        CO_Trials = []; Lum_Trials = []; GAF_Trials = [];
        Saccade_trials = []; Touch_Trials = []; Touch_feed_Trials = [];
        Reach_Trials = Trials; Null_Trials = [];
    end

    for iUnit = 1:length(myClus)
        myClu = myClus(iUnit);
        if grouped == 1
            myspikes = find(spikeTemps == myClu);
        else
            myspikes = find(spikeTemps == myClu - 1);
        end
        RasterData = struct([]);

        if length(myspikes)
            clear CO_Spike Lum_Spike GA_Spike R_Spike N_Spike Saccade_Spike Touch_feed_Spike Touch_Spike mySpikeCell
            clear CO_RT Lum_RT GA_RT R_RT N_RT Saccade_RT Touch_feed__RT Touch_RT myRT

            if ~isempty(CO_Trials)
                try
                    CO_Spike = trialNPSpike(CO_Trials, tower, np, myClu, 'TargsOn', [-300 500], data_root, KSversionflag, grouped);
                    CO_RT = [CO_Trials.SaccStart] - [CO_Trials.TargsOn];
                catch
                    CO_Spike = trialNPSpike(CO_Trials, tower, np, myClu, 'disTargsOn', [-300 500], data_root, KSversionflag, grouped);
                    CO_RT = [CO_Trials.SaccStart] - [CO_Trials.disTargsOn];
                end
            else
                CO_Spike = []; CO_RT = [];
            end

            if ~isempty(Lum_Trials)
                try
                    Lum_Spike = trialNPSpike(Lum_Trials, tower, np, myClu, 'disGo', [-300 500], data_root, KSversionflag, grouped);
                    Lum_RT = [Lum_Trials.SaccStart] - [Lum_Trials.disGo];
                catch
                    Lum_Spike = trialNPSpike(Lum_Trials, tower, np, myClu, 'Go', [-300 500], data_root, KSversionflag, grouped);
                    Lum_RT = [Lum_Trials.SaccStart] - [Lum_Trials.Go];
                end
            else
                Lum_Spike = []; Lum_RT = [];
            end

            if ~isempty(GAF_Trials)
                try
                    GA_Spike = trialNPSpike(GAF_Trials, tower, np, myClu, 'disTargsOn', [-300 500], data_root, KSversionflag, grouped);
                    GA_RT = [GAF_Trials.SaccStart] - [GAF_Trials.disGo];
                catch
                    GA_Spike = trialNPSpike(GAF_Trials, tower, np, myClu, 'TargsOn', [-300 500], data_root, KSversionflag, grouped);
                    GA_RT = [GAF_Trials.SaccStart] - [GAF_Trials.Go];
                end
            else
                GA_Spike = []; GA_RT = [];
            end

            if ~isempty(Saccade_trials)
                try
                    Saccade_Spike = trialNPSpike(Saccade_trials, tower, np, myClu, 'disTargsOn', [-300 500], data_root, KSversionflag, grouped);
                    Saccade_RT = [Saccade_trials.SaccStart] - [Saccade_trials.disGo];
                catch
                    Saccade_Spike = trialNPSpike(Saccade_trials, tower, np, myClu, 'TargsOn', [-300 500], data_root, KSversionflag, grouped);
                    Saccade_RT = [Saccade_trials.SaccStart] - [Saccade_trials.Go];
                end
            else
                Saccade_Spike = []; Saccade_RT = [];
            end

            if ~isempty(Touch_feed_Trials)
                try
                    Touch_feed_Spike = trialNPSpike(Touch_feed_Trials, tower, np, myClu, 'disTargsOn', [-300 500], data_root, KSversionflag, grouped);
                    Touch_feed__RT = [Touch_feed_Trials.SaccStart] - [Touch_feed_Trials.disGo];
                catch
                    Touch_feed_Spike = trialNPSpike(Touch_feed_Trials, tower, np, myClu, 'TargsOn', [-300 500], data_root, KSversionflag, grouped);
                    Touch_feed__RT = [Touch_feed_Trials.SaccStart] - [Touch_feed_Trials.Go];
                end
            else
                Touch_feed_Spike = []; Touch_feed__RT = [];
            end

            if ~isempty(Touch_Trials)
                try
                    Touch_Spike = trialNPSpike(Touch_Trials, tower, np, myClu, 'disTargsOn', [-300 500], data_root, KSversionflag, grouped);
                    Touch_RT = [Touch_Trials.SaccStart] - [Touch_Trials.disGo];
                catch
                    Touch_Spike = trialNPSpike(Touch_Trials, tower, np, myClu, 'TargsOn', [-300 500], data_root, KSversionflag, grouped);
                    Touch_RT = [Touch_Trials.SaccStart] - [Touch_Trials.Go];
                end
                if all(isnan(Touch_RT(:)))
                    Touch_Spike = trialNPSpike(Touch_Trials, tower, np, myClu, 'StartOn', [-300 500], data_root, KSversionflag, grouped);
                    Touch_RT = [Touch_Trials.StartOn] - [Touch_Trials.End];
                end
            else
                Touch_Spike = []; Touch_RT = [];
            end

            if ~isempty(Reach_Trials)
                R_Spike = trialNPSpike(Reach_Trials, tower, np, myClu, 'ReachStart', [-400 400], data_root, KSversionflag, grouped);
                R_RT = [Reach_Trials.ReachStart] - [Reach_Trials.TargsOn];
            else
                R_Spike = []; R_RT = [];
            end

            if ~isempty(Null_Trials)
                N_Spike = trialNPSpike(Null_Trials, tower, np, myClu, 'Pulse_start', [-300 500], data_root, KSversionflag, grouped);
                N_RT = [];
            else
                N_Spike = []; N_RT = [];
            end

            myRT = horzcat(CO_RT, Lum_RT, R_RT, N_RT, GA_RT, Saccade_RT, Touch_feed__RT, Touch_RT);
            mySpikeCell = [CO_Spike; Lum_Spike; R_Spike; N_Spike; GA_Spike; Saccade_Spike; Touch_feed_Spike; Touch_Spike];

            % Other nearby units
            otherspikesClu = find(max_site == max_site(myClu));
            otherspikesClu(otherspikesClu == myClu) = [];
            nOtherClu = length(otherspikesClu);

            if nOtherClu
                myOtherSpikeCell = {};
                myOtherRT = {};
                for iOtherClu = 1:nOtherClu
                    myOtherClu = otherspikesClu(iOtherClu);
                    [OtherSpikeCell, OtherRT] = extract_other_rasters(CO_Trials, Lum_Trials, ...
                        Reach_Trials, Null_Trials, GAF_Trials, Saccade_trials, ...
                        Touch_feed_Trials, Touch_Trials, tower, np, myOtherClu, ...
                        data_root, KSversionflag, grouped);
                    if ~iscell(OtherSpikeCell)
                        OtherSpikeCell = cell(OtherSpikeCell);
                    end
                    myOtherSpikeCell{iOtherClu} = OtherSpikeCell;
                    myOtherRT{iOtherClu} = OtherRT;
                end
            else
                myOtherSpikeCell = [];
                myOtherRT = [];
            end

            RasterData(1).Clu = myClu;
            RasterData(1).SpikeClu = mySpikeCell;
            RasterData(1).OtherClu = otherspikesClu;
            RasterData(1).OtherSpikeClu = myOtherSpikeCell;
            RasterData(1).RT = myRT;
            RasterData(1).OtherRT = myOtherRT;
        else
            RasterData(1).Clu = myClu;
            RasterData(1).SpikeClu = [];
            RasterData(1).OtherClu = [];
            RasterData(1).OtherSpikeClu = [];
            RasterData(1).RT = [];
            RasterData(1).OtherRT = [];
        end

        if isempty(ks_name)
            KSsaveDir = '';
        else
            KSsaveDir = ['KSsave' ks_name];
        end

        if grouped
            output_dir = fullfile(data_root, day, rec_this, rec_name, KSsaveDir);
        else
            output_dir = fullfile(data_root, day, rec_this, KSsaveDir);
        end
        if ~exist(output_dir, 'dir')
            mkdir(output_dir);
        end
        out_file = fullfile(output_dir, ['rec' rec_this '.' tower '.' num2str(np) '.' num2str(myClu) '.' GROUPEDFLAG '.RasterData.mat']);
        save(out_file, 'RasterData', '-v7.3');
        fprintf('Saved: %s\n', out_file);
    end
end

end


function [OtherSpikeCell, OtherRT] = extract_other_rasters(CO_Trials, Lum_Trials, ...
    Reach_Trials, Null_Trials, GAF_Trials, Saccade_trials, ...
    Touch_feed_Trials, Touch_Trials, tower, np, myClu, MonkeyDir, KSversionflag, Grouped)
% Helper to extract rasters for neighboring clusters

    clear CO_Spike Lum_Spike GA_Spike R_Spike N_Spike Saccade_Spike Touch_feed_Spike Touch_Spike
    clear CO_RT Lum_RT GA_RT R_RT N_RT Saccade_RT Touch_feed__RT Touch_RT

    if ~isempty(CO_Trials)
        try
            CO_Spike = trialNPSpike(CO_Trials, tower, np, myClu, 'disTargsOn', [-300 500], MonkeyDir, KSversionflag, Grouped);
            CO_RT = [CO_Trials.SaccStart] - [CO_Trials.disTargsOn];
        catch
            CO_Spike = trialNPSpike(CO_Trials, tower, np, myClu, 'TargsOn', [-300 500], MonkeyDir, KSversionflag, Grouped);
            CO_RT = [CO_Trials.SaccStart] - [CO_Trials.TargsOn];
        end
    else
        CO_Spike = []; CO_RT = [];
    end

    if ~isempty(Lum_Trials)
        try
            Lum_Spike = trialNPSpike(Lum_Trials, tower, np, myClu, 'disGo', [-300 500], MonkeyDir, KSversionflag, Grouped);
            Lum_RT = [Lum_Trials.SaccStart] - [Lum_Trials.disGo];
        catch
            Lum_Spike = trialNPSpike(Lum_Trials, tower, np, myClu, 'Go', [-300 500], MonkeyDir, KSversionflag, Grouped);
            Lum_RT = [Lum_Trials.SaccStart] - [Lum_Trials.Go];
        end
    else
        Lum_Spike = []; Lum_RT = [];
    end

    if ~isempty(Reach_Trials)
        R_Spike = trialNPSpike(Reach_Trials, tower, np, myClu, 'ReachStart', [-400 400], MonkeyDir, KSversionflag, Grouped);
        R_RT = [Reach_Trials.ReachStart] - [Reach_Trials.TargsOn];
    else
        R_Spike = []; R_RT = [];
    end

    if ~isempty(Null_Trials)
        N_Spike = trialNPSpike(Null_Trials, tower, np, myClu, 'Pulse_start', [-300 500], MonkeyDir, KSversionflag, Grouped);
        N_RT = [];
    else
        N_Spike = []; N_RT = [];
    end

    if ~isempty(GAF_Trials)
        try
            GA_Spike = trialNPSpike(GAF_Trials, tower, np, myClu, 'disTargsOn', [-300 500], MonkeyDir, KSversionflag, Grouped);
            GA_RT = [GAF_Trials.SaccStart] - [GAF_Trials.disGo];
        catch
            GA_Spike = trialNPSpike(GAF_Trials, tower, np, myClu, 'TargsOn', [-300 500], MonkeyDir, KSversionflag, Grouped);
            GA_RT = [GAF_Trials.SaccStart] - [GAF_Trials.Go];
        end
    else
        GA_Spike = []; GA_RT = [];
    end

    if ~isempty(Saccade_trials)
        try
            Saccade_Spike = trialNPSpike(Saccade_trials, tower, np, myClu, 'disTargsOn', [-300 500], MonkeyDir, KSversionflag, Grouped);
            Saccade_RT = [Saccade_trials.SaccStart] - [Saccade_trials.disGo];
        catch
            Saccade_Spike = trialNPSpike(Saccade_trials, tower, np, myClu, 'TargsOn', [-300 500], MonkeyDir, KSversionflag, Grouped);
            Saccade_RT = [Saccade_trials.SaccStart] - [Saccade_trials.Go];
        end
    else
        Saccade_Spike = []; Saccade_RT = [];
    end

    if ~isempty(Touch_feed_Trials)
        try
            Touch_feed_Spike = trialNPSpike(Touch_feed_Trials, tower, np, myClu, 'disTargsOn', [-300 500], MonkeyDir, KSversionflag, Grouped);
            Touch_feed__RT = [Touch_feed_Trials.SaccStart] - [Touch_feed_Trials.disGo];
        catch
            Touch_feed_Spike = trialNPSpike(Touch_feed_Trials, tower, np, myClu, 'TargsOn', [-300 500], MonkeyDir, KSversionflag, Grouped);
            Touch_feed__RT = [Touch_feed_Trials.SaccStart] - [Touch_feed_Trials.Go];
        end
    else
        Touch_feed_Spike = []; Touch_feed__RT = [];
    end

    if ~isempty(Touch_Trials)
        try
            Touch_Spike = trialNPSpike(Touch_Trials, tower, np, myClu, 'disTargsOn', [-300 500], MonkeyDir, KSversionflag, Grouped);
            Touch_RT = [Touch_Trials.SaccStart] - [Touch_Trials.disGo];
        catch
            Touch_Spike = trialNPSpike(Touch_Trials, tower, np, myClu, 'TargsOn', [-300 500], MonkeyDir, KSversionflag, Grouped);
            Touch_RT = [Touch_Trials.SaccStart] - [Touch_Trials.Go];
        end
        if all(isnan(Touch_RT(:)))
            Touch_Spike = trialNPSpike(Touch_Trials, tower, np, myClu, 'StartOn', [-300 500], MonkeyDir, KSversionflag, Grouped);
            Touch_RT = [Touch_Trials.StartOn] - [Touch_Trials.End];
        end
    else
        Touch_Spike = []; Touch_RT = [];
    end

    OtherSpikeCell = [CO_Spike; Lum_Spike; R_Spike; N_Spike; GA_Spike; Saccade_Spike; Touch_feed_Spike; Touch_Spike];
    OtherRT = horzcat(CO_RT, Lum_RT, R_RT, N_RT, GA_RT, Saccade_RT, Touch_feed__RT, Touch_RT);
end
