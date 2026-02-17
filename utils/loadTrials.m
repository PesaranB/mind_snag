function Trials = loadTrials(day, rec, data_root)
% LOADTRIALS Load behavioral trial data for a recording day
%
%   Trials = loadTrials(day, rec, data_root)
%
%   Parameters:
%     day       - Recording date (YYMMDD string)
%     rec       - Recording number (string or cell), optional
%     data_root - Root data directory (replaces MONKEYDIR)
%
%   Returns:
%     Trials - Struct array of trial data

Trials = struct([]);
trfile = fullfile(data_root, day, 'mat/Trials.mat');
if isfile(trfile)
    load(trfile);
    if nargin > 1 && ~isempty(rec)
        Recs = {Trials.Rec};
        if iscell(rec)
            nRec = length(rec);
            ind = [];
            for iRec = 1:nRec
                ind = [ind, find(strcmp(Recs, rec{iRec}))];
            end
        else
            ind = find(strcmp(Recs, rec));
        end
        Trials = Trials(ind);
    end
else
    Trials = [];
    warning('mind_snag:io', 'No Trials data saved for %s at %s', day, trfile);
end

end
