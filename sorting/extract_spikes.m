function extract_spikes(cfg, day, rec, tower, np, grouped)
% EXTRACT_SPIKES Extract spike times from Kilosort output with drift correction
%
%   extract_spikes(cfg, day, rec, tower, np, grouped)
%
%   Loads Kilosort results, applies two-stage drift correction
%   (AP -> NIDQ -> recording timebase), and saves structured cluster data.
%
%   Parameters:
%     cfg     - Configuration struct from mind_snag_config
%     day     - Recording date as string, YYMMDD format (e.g. '250224')
%     rec     - Recording number(s), string or cell array (e.g. '007' or {'007','009'})
%     tower   - Recording setup name (e.g. 'LPPC_LPFC_modularV1')
%     np      - Neuropixel probe number (1 or 2)
%     grouped - 0 for individual recordings, 1 for concatenated
%
%   Outputs:
%     Saves rec{rec}.{tower}.{np}.{GroupFlag}.NPclu.mat containing:
%       NPclu      - [spike_time, cluster_id] matrix (drift-corrected)
%       NPtemplate - Template shapes [nTemplates x nTimePoints x nChannels]
%       Clu_info   - [cluster_id, channel_index] mapping
%       KSclu_info - Good units only (KS label = 'good')
%       pcFeat     - PC features for each spike
%       tempScalingAmps - Template scaling amplitudes
%       KSversion  - Kilosort version number
%
%   See also: run_kilosort4, compute_isolation, mind_snag_config

data_root = cfg.data_root;
assert(~isempty(data_root), 'mind_snag:config', 'cfg.data_root must be set.');

if ~exist('grouped', 'var'); grouped = 0; end

if cfg.ks_version == 4
    ks_name = '_KS4';
else
    ks_name = '';
end

KSversionflag = (cfg.ks_version == 4);

group_rec_dir = fullfile(data_root, day, 'spikeglx_data', ...
    ['grouped_recordings.' tower '.' num2str(np)]);

if grouped
    rec_name = strjoin(rec, '_');
    GROUPEDFLAG = 'Grouped';
else
    rec_name = rec;
    GROUPEDFLAG = 'NotGrouped';
end

ks_dir = fullfile(group_rec_dir, ['group' rec_name ks_name]);
assert(exist(ks_dir, 'dir') == 7, 'mind_snag:io', ...
    'Kilosort output directory not found: %s\nRun run_kilosort4 first.', ks_dir);

params.excludeNoise = false;
sp = loadKSdir(ks_dir, params);

groupfile = fullfile(group_rec_dir, ['spike_sorting_rec_groups_' rec_name '.mat']);
[max_site, ~] = clus_channel_infor(cfg, day, rec, tower, np, grouped);

if exist(groupfile, 'file') && grouped == 1
    load(groupfile, 'grouped_recs');
    ngroups = length(grouped_recs);

    for igroup = 1:ngroups
        group = grouped_recs{igroup};
        theo_offset = 0;

        for iR = 1:length(group)
            rec_this = rec{iR};
            rec_dir = fullfile(data_root, day, rec_this);
            output_dir = fullfile(data_root, day, rec_this);

            if ~exist(output_dir, 'dir')
                mkdir(output_dir);
            end

            ap_meta_file = fullfile(rec_dir, ['rec' rec_this '.' tower '.' num2str(np) '.ap_meta.mat']);
            nidq_meta_file = fullfile(rec_dir, ['rec' rec_this '.nidq_meta.mat']);
            assert(exist(ap_meta_file, 'file') == 2, 'mind_snag:io', ...
                'AP meta file not found: %s', ap_meta_file);
            load(ap_meta_file, 'ap_meta');
            load(nidq_meta_file);

            clear l_st_select st_select
            theo_dur = ap_meta.nsamp ./ ap_meta.Fs;
            l_st_select = sp.st <= theo_offset + theo_dur & sp.st > theo_offset;
            st_select = sp.st(l_st_select) - theo_offset;
            w_nidq = ap_meta.nidq_drift_model_weights;

            if ~isfield(nidq_meta, 'rec_drift_model_weights')
                warning('mind_snag:drift', ...
                    'nidq_meta missing rec_drift_model_weights for rec %s. Skipping drift correction.', rec_this);
            else
                theo_offset = theo_offset + theo_dur;
            end

            w_rec = nidq_meta.rec_drift_model_weights;
            clear st_select_nidq new_spiketimes new_spikeTemplates
            st_select_nidq = w_nidq(1) + w_nidq(2) * st_select;
            new_spiketimes = w_rec(1) + w_rec(2) * st_select_nidq;
            new_spikeTemplates = sp.spikeTemplates(l_st_select);
            pcFeat = sp.pcFeat(l_st_select, 1:3, :);
            tempScalingAmps = sp.tempScalingAmps(l_st_select);

            clear NPclu
            NPclu = zeros(length(new_spiketimes), 2);
            NPclu(:,1) = new_spiketimes;
            NPclu(:,2) = new_spikeTemplates + 1;
            NPtemplate = sp.temps;
            clu_id = unique(sp.clu) + 1;
            channelNum_ind = max_site;

            ksFile = fullfile(ks_dir, 'cluster_KSLabel.tsv');
            [cids, cgs] = readClusterGroupsCSV(ksFile);
            KS_cluid = cids(cgs == 2) + 1;

            clear Clu_info KSclu_info
            Clu_info(:,1) = clu_id;
            Clu_info(:,2) = channelNum_ind(clu_id);
            KSclu_info(:,1) = clu_id;
            KSclu_info(:,2) = channelNum_ind;
            KSversion = cfg.ks_version;

            out_file = fullfile(output_dir, ['rec' rec_this '.' tower '.' num2str(np) '.' GROUPEDFLAG '.NPclu.mat']);
            fprintf('Saving: %s\n', out_file);
            save(out_file, 'NPclu', 'NPtemplate', 'Clu_info', 'KSclu_info', ...
                'pcFeat', 'tempScalingAmps', 'KSversion', '-v7.3');
        end
    end

elseif exist(groupfile, 'file') && grouped == 0
    load(groupfile, 'grouped_recs');

    rec_this = rec;
    rec_dir = fullfile(data_root, day, rec_this);

    try
        ap_meta_file = fullfile(rec_dir, ['rec' rec '.' tower '.' num2str(np) '.ap_meta.mat']);
        nidq_meta_file = fullfile(rec_dir, ['rec' rec '.nidq_meta.mat']);
        load(ap_meta_file, 'ap_meta');
        load(nidq_meta_file);
    catch
        ap_meta_file = fullfile(rec_dir, ['rec' rec '.' tower '.ap_meta.mat']);
        nidq_meta_file = fullfile(rec_dir, ['rec' rec '.nidq_meta.mat']);
        load(ap_meta_file, 'ap_meta');
        load(nidq_meta_file);
    end

    theo_offset = 0;
    clear l_st_select st_select
    theo_dur = ap_meta.nsamp ./ ap_meta.Fs;

    l_st_select = sp.st < theo_offset + theo_dur & sp.st > theo_offset;
    st_select = sp.st(l_st_select) - theo_offset;

    w_nidq = ap_meta.nidq_drift_model_weights;

    if ~isfield(nidq_meta, 'rec_drift_model_weights')
        warning('mind_snag:drift', ...
            'nidq_meta missing rec_drift_model_weights. Check procAlignSourcesToRos.');
    end

    w_rec = nidq_meta.rec_drift_model_weights;

    clear st_select_nidq new_spiketimes new_spikeTemplates
    st_select_nidq = w_nidq(1) + w_nidq(2) * st_select;
    new_spiketimes = w_rec(1) + w_rec(2) * st_select_nidq;
    new_spikeTemplates = sp.spikeTemplates(l_st_select);

    NPclu = zeros(length(new_spiketimes), 2);
    NPclu(:,1) = new_spiketimes;
    NPclu(:,2) = new_spikeTemplates + 1;

    NPtemplate = sp.temps;
    pcFeat = sp.pcFeat(l_st_select, 1:3, :);
    tempScalingAmps = sp.tempScalingAmps(l_st_select);

    clu_id = unique(sp.clu) + 1;
    channelNum_ind = max_site;
    Clu_info(:,1) = clu_id;
    Clu_info(:,2) = channelNum_ind;

    ksFile = fullfile(ks_dir, 'cluster_KSLabel.tsv');
    [cids, cgs] = readClusterGroupsCSV(ksFile);
    KS_cluid = cids(cgs == 2) + 1;
    mask = ismember(Clu_info(:,1), KS_cluid);
    KSclu_info(:,1) = clu_id(mask);
    KSclu_info(:,2) = channelNum_ind(mask);

    KSversion = cfg.ks_version;

    output_dir = fullfile(data_root, day, rec_this);
    if ~exist(output_dir, 'dir')
        mkdir(output_dir);
    end

    out_file = fullfile(output_dir, ['rec' rec_this '.' tower '.' num2str(np) '.' GROUPEDFLAG '.NPclu.mat']);
    fprintf('Saving: %s\n', out_file);
    save(out_file, 'NPclu', 'NPtemplate', 'Clu_info', 'KSclu_info', ...
        'pcFeat', 'tempScalingAmps', 'KSversion', '-v7.3');
end

end
