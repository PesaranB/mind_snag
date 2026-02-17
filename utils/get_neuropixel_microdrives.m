function [np_drives, np_indices] = get_neuropixel_microdrives(experiment)
% GET_NEUROPIXEL_MICRODRIVES Extract Neuropixel microdrives from experiment
%
%   [np_drives, np_indices] = get_neuropixel_microdrives(experiment)
%
%   Filters the experiment.hardware structure to find Neuropixel probes.
%
%   Parameters:
%     experiment - Experiment struct from loadExperiment
%
%   Returns:
%     np_drives  - Filtered microdrive structures (Neuropixel only)
%     np_indices - Indices into experiment.hardware.microdrive
%
%   See also: trialNPSpike, loadExperiment

np_drives = [];
np_indices = [];

if isempty(experiment) || ~isfield(experiment, 'hardware')
    return;
end

if ~isfield(experiment.hardware, 'microdrive')
    return;
end

drives = experiment.hardware.microdrive;
np_types = {'NP4L', 'Neuropixel', 'NP1', 'NP6', 'modularV1'};

for i = 1:length(drives)
    isNP = false;
    if isfield(drives(i), 'type')
        isNP = any(strcmpi(drives(i).type, np_types));
    end
    if ~isNP && isfield(drives(i), 'name')
        isNP = ~isempty(regexp(drives(i).name, 'NP|neuropix|modular', 'once'));
    end
    if isNP
        np_drives = [np_drives, drives(i)];
        np_indices = [np_indices, i];
    end
end

end
