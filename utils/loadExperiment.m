function experiment = loadExperiment(day, rec, MonkeyDir)
% LOADEXPERIMENT Load experiment definition from .experiment.mat
%
%   experiment = loadExperiment(day, rec)
%   experiment = loadExperiment(day, rec, MonkeyDir)
%
%   Parameters:
%     day       - Recording date (YYMMDD string)
%     rec       - Recording number (string). If empty, uses first recording.
%     MonkeyDir - Data root directory (default: global MONKEYDIR)
%
%   Returns:
%     experiment - Experiment struct, or empty if file not found
%
%   See also: trialNPSpike

global MONKEYDIR

if nargin < 3 || isempty(MonkeyDir)
    MonkeyDir = MONKEYDIR;
end

if nargin < 2 || isempty(rec)
    recs = dayrecs(day, MonkeyDir);
    if ~isempty(recs)
        rec = recs{1};
    else
        experiment = [];
        return;
    end
end

expFile = fullfile(MonkeyDir, day, rec, ['rec' rec '.experiment.mat']);

if exist(expFile, 'file')
    loaded = load(expFile, 'experiment');
    experiment = loaded.experiment;
else
    experiment = [];
end

end
