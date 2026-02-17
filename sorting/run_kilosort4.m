function run_kilosort4(cfg, day, override, rec, tower, np, grouped)
% RUN_KILOSORT4 Execute Kilosort4 spike sorting on SpikeGLX recordings
%
%   run_kilosort4(cfg, day, override, rec, tower, np, grouped)
%
%   Concatenates SpikeGLX .bin files (if grouped), then runs Kilosort4
%   via a Python virtualenv to produce spike sorting results.
%
%   Parameters:
%     cfg      - Configuration struct from mind_snag_config
%     day      - Recording date as string, YYMMDD format (e.g. '250224')
%     override - Logical. If true, re-concatenate even if combined file exists
%     rec      - Cell array of recording numbers (e.g. {'007','009','010'})
%     tower    - Recording setup name (e.g. 'LPPC_LPFC_modularV1')
%     np       - Neuropixel probe number (1 or 2)
%     grouped  - 0 for individual recordings, 1 for concatenated
%
%   Requires:
%     - Python virtualenv with kilosort[gui]==4.0.22 at cfg.kilosort_venv
%     - Probe file at cfg.probe_file
%     - Run_kilosort4.py at cfg.kilosort_script
%
%   See also: extract_spikes, mind_snag_config

% Validate inputs
assert(~isempty(cfg.data_root), 'mind_snag:config', ...
    'cfg.data_root must be set. Run mind_snag_config first.');
assert(~isempty(cfg.kilosort_venv), 'mind_snag:config', ...
    'cfg.kilosort_venv must be set to your Python virtualenv path.');
assert(exist(cfg.data_root, 'dir') == 7, 'mind_snag:io', ...
    'Data root not found: %s', cfg.data_root);

data_root = cfg.data_root;
gpu = cfg.gpu;

grouped_recs{1} = rec;
ngroups = length(grouped_recs);

%% Create grouped recordings directory
group_rec_dir = fullfile(data_root, day, 'spikeglx_data', ...
    sprintf('grouped_recordings.%s.%d', tower, np));

if ~exist(group_rec_dir, 'dir')
    mkdir(group_rec_dir);
end

fprintf('Saving spike sorting rec groups\n');
if grouped
    grouped_name = strjoin(rec, '_');
    save(fullfile(group_rec_dir, ...
        ['spike_sorting_rec_groups_' grouped_name '.mat']), ...
        'grouped_recs');
else
    grouped_name = rec{1};
    save(fullfile(group_rec_dir, ...
        ['spike_sorting_rec_groups_' rec{1} '.mat']), 'grouped_recs');
end

%% Concatenate input data
for igroup = 1:ngroups
    group = grouped_recs{igroup};
    if grouped == 0
        group = {group};
    end
    imec_rec_dirs = {};
    sglx_files_to_join = {};
    ap_metas = {};

    nsamp_total = 0;

    for iR = 1:length(group)
        ap_meta_file = fullfile(data_root, day, rec{iR}, ...
            sprintf('rec%s.%s.%d.ap_meta.mat', rec{iR}, tower, np));
        assert(exist(ap_meta_file, 'file') == 2, 'mind_snag:io', ...
            'AP meta file not found: %s', ap_meta_file);

        load(ap_meta_file, 'ap_meta');

        ap_metas{iR} = ap_meta;
        nsamp_total = nsamp_total + ap_meta.nsamp;
        [pathstr, ~, ~] = fileparts(ap_meta.fileName);
        dirs = strsplit(pathstr, '/');
        match_idx = find(~cellfun('isempty', regexp(dirs, 'rec')));
        sglx_rec = dirs{match_idx};

        if isfield(ap_meta, 'imec_used_probe_name')
            imec_rec_dir = fullfile(data_root, day, ...
                'spikeglx_data', sglx_rec, ...
                [sglx_rec, sprintf('_%s', ap_meta.imec_used_probe_name)]);
            ap_bin_name = [sglx_rec, sprintf('_t0.%s.ap.bin', ...
                ap_meta.imec_used_probe_name)];
        elseif isfield(ap_meta, 'used_probe_name')
            imec_rec_dir = fullfile(data_root, day, ...
                'spikeglx_data', sglx_rec, ...
                [sglx_rec, sprintf('_%s', ap_meta.used_probe_name)]);
            ap_bin_name = [sglx_rec, sprintf('_t0.%s.ap.bin', ...
                ap_meta.used_probe_name)];
        else
            warning('mind_snag:probe', 'Probe name missing; assuming imec0');
            ap_meta.imec_used_probe_name = 'imec0';
            imec_rec_dir = fullfile(data_root, day, ...
                'spikeglx_data', sglx_rec, ...
                [sglx_rec, sprintf('_%s', ap_meta.imec_used_probe_name)]);
            ap_bin_name = [sglx_rec, sprintf('_t0.%s.ap.bin', ...
                ap_meta.imec_used_probe_name)];
        end

        if contains(ap_bin_name, 'reco')
            ap_bin_name = strrep(ap_bin_name, 'reco', 'rec');
        end
        if contains(imec_rec_dir, 'reco')
            imec_rec_dir = strrep(imec_rec_dir, 'reco', 'rec');
        end

        imec_rec_dirs{iR} = imec_rec_dir;
        sglx_files_to_join{iR} = ap_bin_name;
    end

    nchan = ap_meta.nchan;

    %% Copy and merge files
    group_rec_input_dir = fullfile(data_root, day, 'spikeglx_data', ...
        sprintf('rec%s', grouped_name), ...
        sprintf('rec%s_imec%d', grouped_name, (np-1)));
    if ~exist(group_rec_input_dir, 'dir')
        mkdir(group_rec_input_dir);
    end

    combined_ap_bin = fullfile(group_rec_input_dir, ...
        sprintf('combined_ap_group%s.bin', grouped_name));

    expected_bytes = nsamp_total * nchan * 2;

    combined_ap_exists = false;
    if exist(combined_ap_bin, 'file')
        file_info = dir(combined_ap_bin);
        if file_info.bytes == expected_bytes
            combined_ap_exists = true;
            fprintf('  Combined AP file already written\n');
        end
    end

    if ~combined_ap_exists || override
        fid = fopen(combined_ap_bin, 'w');
        fclose(fid);
        fid = fopen(combined_ap_bin, 'a');

        for iR = 1:length(group)
            fprintf('  Memory mapping rec %s\n', rec{iR});
            m_ap = sglx_util.memmap(ap_metas{iR}, sglx_files_to_join{iR}, ...
                imec_rec_dirs{iR});
            nsamp = size(m_ap.Data.x, 2);
            blocksize = 500;
            nblocks = ceil(nsamp / blocksize);
            fprintf('  Writing data\n');
            for iblock = 1:nblocks
                idx = (iblock-1)*blocksize + 1 : min(nsamp, iblock*blocksize);
                fwrite(fid, m_ap.Data.x(:, idx), 'int16');
            end
        end
        fclose(fid);
    end
end

%% Generate Kilosort4 output folder
if grouped == 1
    KS_result_dir = fullfile(group_rec_dir, ['group', grouped_name '_KS4']);
else
    KS_result_dir = fullfile(group_rec_dir, ['group', rec{1} '_KS4']);
end
if ~exist(KS_result_dir, 'dir')
    mkdir(KS_result_dir);
end

%% Determine input data
if grouped == 1
    fprintf('Input: concatenated recordings %s\n', grouped_name);
    InputData = combined_ap_bin;
else
    recordings_excel_file = fullfile(data_root, 'excel', 'valid_recordings.xlsx');
    assert(exist(recordings_excel_file, 'file') == 2, 'mind_snag:io', ...
        'Recording metadata not found: %s', recordings_excel_file);
    all_records = excel_table_to_struct_array(recordings_excel_file);
    matching_indices = strcmp({all_records.Day}, day);
    records_for_specific_day = all_records(matching_indices);
    matching_indices_Rec = strcmp({records_for_specific_day.Rec}, rec);
    records_for_specific_day_rec = records_for_specific_day(matching_indices_Rec);
    Sglx = records_for_specific_day_rec.SglxRec;
    InputData = fullfile(data_root, day, 'spikeglx_data', Sglx, ...
        [Sglx, '_imec', num2str(np-1)], ...
        [Sglx, '_t0.imec', num2str(np-1), '.ap.bin']);
end

resultsDir = KS_result_dir;
fprintf('Input: %s\n', InputData);
fprintf('Output: %s\n', resultsDir);

assert(exist(InputData, 'file') == 2, 'mind_snag:io', ...
    'Input binary not found: %s', InputData);

%% Run Kilosort4 via Python
scriptName = cfg.kilosort_script;
probeFile = cfg.probe_file;
paramsDir = cfg.ks_params_dir;
venvPath = cfg.kilosort_venv;

assert(exist(venvPath, 'dir') == 7, 'mind_snag:config', ...
    'Python virtualenv not found: %s', venvPath);

fprintf('Starting Kilosort4...\n');
command = sprintf(['bash -lc "source %s/bin/activate && ' ...
    'export OPENBLAS_NUM_THREADS=%d && ' ...
    'python \\"%s\\" --results \\"%s\\" --probe \\"%s\\" ' ...
    '--params \\"%s\\" --data \\"%s\\" --gpu %d"'], ...
    venvPath, cfg.n_threads, scriptName, resultsDir, probeFile, ...
    paramsDir, InputData, gpu);

[status, cmdOut] = system(command);

if status ~= 0
    warning('mind_snag:kilosort', 'Kilosort4 exited with status %d:\n%s', status, cmdOut);
else
    fprintf('Kilosort4 completed successfully.\n');
end

end
