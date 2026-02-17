function recs = dayrecs(day, MonkeyDir)
% DAYRECS List all recording directories for a given day
%
%   recs = dayrecs(day, MonkeyDir)
%
%   Parameters:
%     day       - Recording date (YYMMDD string)
%     MonkeyDir - Data root directory
%
%   Returns:
%     recs - Cell array of recording directory names (e.g. {'007','009','010'})
%
%   See also: trialNPSpike, loadTrials

global MONKEYDIR

if nargin < 2 || isempty(MonkeyDir)
    MonkeyDir = MONKEYDIR;
end

dayDir = fullfile(MonkeyDir, day);
recs = {};

if ~exist(dayDir, 'dir')
    return;
end

% Look for recording directories matching patterns 0*, 1*..8*
patterns = {'0*', '1*', '2*', '3*', '4*', '5*', '6*', '7*', '8*'};
for ip = 1:length(patterns)
    d = dir(fullfile(dayDir, patterns{ip}));
    d = d([d.isdir]);
    for id = 1:length(d)
        if ~strcmp(d(id).name, '.') && ~strcmp(d(id).name, '..')
            recs{end+1} = d(id).name; %#ok<AGROW>
        end
    end
end

recs = sort(recs);

end
