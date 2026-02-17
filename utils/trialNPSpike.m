function [Spike] = trialNPSpike(Trials, sys, np, cl, field, bn, MonkeyDir, KSversionflag, Grouped)
% TRIALNPSPIKE Load trial-aligned Neuropixel spike data
%
%   Spike = trialNPSpike(Trials, sys, np, cl, field, bn, MonkeyDir)
%   Spike = trialNPSpike(Trials, sys, np, cl, field, bn, MonkeyDir, KSversionflag, Grouped)
%
%   Loads spike times from NPclu.mat files for specified clusters, aligns
%   them to behavioral trial events (e.g. 'TargsOn', 'ReachAq').
%
%   Parameters:
%     Trials         - Trials data structure (array of structs)
%     sys            - System/tower name (string or cell)
%     np             - Neuropixel probe number (default: 1)
%     cl             - Cluster ID(s) to load (default: 1)
%     field          - Event name to align to (default: 'TargsOn')
%     bn             - Time window [start, stop] in ms (default: [-500, 500])
%     MonkeyDir      - Data root directory (replaces MONKEYDIR global)
%     KSversionflag  - Kilosort version: 4 for KS4, 1 for KS1, 0 for KS2.5
%     Grouped        - 0 for individual, 1 for grouped recordings
%
%   Returns:
%     Spike - {nTrials x nClusters} cell array of spike times in ms
%
%   See also: extract_rasters, loadTrials

global MONKEYDIR experiment
day = Trials(1).Day;
rec = Trials(1).Rec;
experiment = loadExperiment(day, rec);
[~, i_np_towers] = get_neuropixel_microdrives(experiment);

if nargin < 2 || isempty(sys); sys = Trials(1).MT{i_np_towers}; end
if nargin < 3 || isempty(np); np = 1; end
if nargin < 4 || isempty(cl); cl = 1; end
if nargin < 5 || isempty(field); field = 'TargsOn'; end
if nargin < 6 || isempty(bn); bn = [-500,500]; end
if nargin < 7 || isempty(MonkeyDir); MonkeyDir = MONKEYDIR; end
if nargin < 8 || isempty(KSversionflag); KSversionflag = []; end
if nargin < 9 || isempty(Grouped); Grouped = 0; end

if ischar(sys)
    sysnum = findSys(Trials, sys);
end

nCl = length(cl);
nTotalTr = length(Trials);

if strcmp(field, 'PulseStarts')
    Spike = {};
else
    Spike = cell(nTotalTr, nCl);
end

Recs = getRec(Trials);
day = Trials(1).Day;
recs = dayrecs(day, MonkeyDir);
nRecs = length(recs);
if ~ischar(field); error('mind_snag:arg', 'FIELD needs to be a string'); end

if iscell(sys)
    sys = sys{1};
end

for iRecs = 1:nRecs
    rec = recs{iRecs};
    RecTrials = find(strcmp(Recs, rec));
    nTr = length(RecTrials);
    if nTr
        EventsFile = fullfile(MonkeyDir, day, rec, ['rec' rec '.Events.mat']);
        SpontEventsFile = fullfile(MonkeyDir, day, rec, ['rec' rec '.SpontEvents.mat']);
        MocapEventsFile = fullfile(MonkeyDir, day, rec, ['rec' rec '.MocapEvents.mat']);
        SequenceEventsFile = fullfile(MonkeyDir, day, rec, ['rec' rec '.SequenceEvents.mat']);

        if exist(SequenceEventsFile, 'file')
            load(SequenceEventsFile, 'SequenceEvents');
            Events = SequenceEvents;
        elseif exist(EventsFile, 'file')
            load(EventsFile, 'Events');
            MONKEYDIR = MonkeyDir;
        elseif exist(SpontEventsFile, 'file')
            load(SpontEventsFile, 'SpontEvents');
            Events = SpontEvents;
        elseif exist(MocapEventsFile, 'file')
            load(MocapEventsFile, 'MocapEvents');
            Events = MocapEvents;
        end

        if Grouped
            GROUPEDFLAG = 'Grouped';
        else
            GROUPEDFLAG = 'NotGrouped';
        end

        if KSversionflag == 4
            ks_name = 'KSsave_KS4';
            KSsaveDir = fullfile(ks_name);
            NPclu_filename = fullfile(MonkeyDir, day, rec, KSsaveDir, ...
                ['rec' rec '.' sys '.' num2str(np) '.' GROUPEDFLAG '.NPclu.mat']);
        elseif KSversionflag == 1
            NPclu_filename = fullfile(MonkeyDir, day, rec, ...
                ['rec' num2str(rec) '.' sys '.' num2str(np) '.' GROUPEDFLAG '.NPclu.mat']);
        elseif KSversionflag == 0 || isempty(KSversionflag)
            NPclu_filename = fullfile(MonkeyDir, day, rec, ...
                ['rec' num2str(rec) '.' sys '.' num2str(np) '.NPclu.mat']);
        elseif KSversionflag == 1.5
            ks_name = 'KSsave_KS';
            KSsaveDir = fullfile(ks_name);
            NPclu_filename = fullfile(MonkeyDir, day, rec, KSsaveDir, ...
                ['rec' rec '.' sys '.' num2str(np) '.NPclu.mat']);
        end

        if exist(NPclu_filename, 'file')
            load(NPclu_filename);
        end

        for iTr = 1:nTr
            tr = RecTrials(iTr);
            subtrial = Trials(tr).Trial;
            for iCl = 1:nCl
                Spike(tr, iCl) = loadnpspike(NPclu, Events, subtrial, field, bn, cl(iCl));
            end
        end
    end
end

end
