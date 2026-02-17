function [Spike] = loadnpspike(NPclu, Events, subtrial, field, bn, cl)
% LOADNPSPIKE Load spike times for a single trial and cluster
%
%   Spike = loadnpspike(NPclu, Events, subtrial, field, bn, cl)
%
%   Extracts spike times from NPclu data aligned to a behavioral event
%   for a single trial.
%
%   Parameters:
%     NPclu    - [spike_time, cluster_id] matrix (drift-corrected)
%     Events   - Events structure with trial timing information
%     subtrial - Trial index within this recording
%     field    - Event name to align to (e.g. 'TargsOn')
%     bn       - Time window [start, stop] in ms
%     cl       - Cluster ID to extract
%
%   Returns:
%     Spike - Cell containing spike times (ms) relative to event
%
%   See also: trialNPSpike

Fs = 30000;  % Neuropixel sampling rate

if isempty(NPclu)
    Spike = {[]};
    return;
end

% Get event time for this trial
if isfield(Events, field)
    eventTimes = Events.(field);
    if subtrial > length(eventTimes)
        Spike = {[]};
        return;
    end
    eventTime = eventTimes(subtrial);
else
    Spike = {[]};
    return;
end

if isnan(eventTime) || eventTime == 0
    Spike = {[]};
    return;
end

% Convert event time to samples
eventSample = eventTime * Fs / 1000;  % ms to samples

% Find spikes for this cluster
cluSpikes = NPclu(NPclu(:,2) == cl, 1);

% Find spikes in window around event
startSample = eventSample + bn(1) * Fs / 1000;
endSample = eventSample + bn(2) * Fs / 1000;

windowSpikes = cluSpikes(cluSpikes >= startSample & cluSpikes <= endSample);

% Convert to ms relative to event
spikeTimes = (windowSpikes - eventSample) * 1000 / Fs;

Spike = {spikeTimes};

end
