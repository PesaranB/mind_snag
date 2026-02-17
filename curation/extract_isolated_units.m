function extract_isolated_units(cfg, day, rec, tower, np, grouped)
% EXTRACT_ISOLATED_UNITS Identify isolated units from SortData and update NPclu
%
%   extract_isolated_units(cfg, day, rec, tower, np, grouped)
%
%   Scans all SortData files for units marked as isolated (UnitIso == 1),
%   extracts their spikes from NPclu, and saves NPisoclu back into NPclu.mat.
%
%   Parameters:
%     cfg     - Configuration struct from mind_snag_config
%     day     - Recording date (YYMMDD string)
%     rec     - Recording number(s), string or cell array
%     tower   - Recording setup name
%     np      - Neuropixel probe number (1 or 2)
%     grouped - 0 for individual, 1 for concatenated
%
%   See also: compute_isolation, extract_spikes

data_root = cfg.data_root;

if cfg.ks_version == 4
    KSname = '/KSsave_KS4';
else
    KSname = '';
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

for i = 1:nR
    if nR == 1
        rec = {rec};
    end
    rec_this = rec{i};

    folderName = fullfile(data_root, day, rec_this, ...
        ['rec' rec_this '.' tower '.' num2str(np) '.' GROUPEDFLAG]);

    fprintf('Loading: %s.NPclu.mat\n', folderName);
    load([folderName, '.NPclu.mat']);
    cluIds = unique(double(NPclu(:,2)));
    IsoCluIds = [];

    for ic = 1:length(cluIds)
        clear tmpClu fileIso SortData
        tmpClu = cluIds(ic);
        if grouped
            fileIso = fullfile(data_root, day, rec_this, rec_name, KSname, ...
                ['rec' rec_this '.' tower '.' num2str(np) '.' num2str(tmpClu) '.' GROUPEDFLAG '.SortData.mat']);
        else
            fileIso = fullfile(data_root, day, rec_this, KSname, ...
                ['rec' rec_this '.' tower '.' num2str(np) '.' num2str(tmpClu) '.' GROUPEDFLAG '.SortData.mat']);
        end

        if ~exist(fileIso, 'file')
            warning('mind_snag:io', 'SortData not found: %s', fileIso);
            continue;
        end

        SortData = load(fileIso);
        SortData = SortData.SortData;

        if SortData(1).UnitIso == 1
            IsoCluIds = cat(2, IsoCluIds, tmpClu);
        end
    end

    % Generate NPisoclu
    NpIsoClu = nan(length(NPclu), 2);
    for ii = 1:length(IsoCluIds)
        tmp = IsoCluIds(ii);
        tmpInd = find(NPclu(:,2) == tmp);
        NpIsoClu(tmpInd, 1) = NPclu(tmpInd, 1);
        NpIsoClu(tmpInd, 2) = NPclu(tmpInd, 2);
    end

    nan_ind = find(isnan(NpIsoClu(:,1)));
    NpIsoClu(nan_ind,:) = [];

    Clu_info = double(Clu_info);
    IsoClu_Info = nan(length(IsoCluIds), 2);
    IsoCluInd = find(ismember(Clu_info(:,1), IsoCluIds));

    IsoClu_Info(:,1) = Clu_info(IsoCluInd, 1);
    IsoClu_Info(:,2) = Clu_info(IsoCluInd, 2);

    NPisoclu = NpIsoClu;
    IsoClu_info = IsoClu_Info;

    save([folderName, '.NPclu.mat'], 'NPclu', 'NPtemplate', 'Clu_info', ...
        'KSclu_info', 'pcFeat', 'tempScalingAmps', 'NPisoclu', 'IsoClu_info', ...
        'KSversion', '-v7.3');

    fprintf('Saved %d isolated units for rec %s\n', length(IsoCluIds), rec_this);
end

end
