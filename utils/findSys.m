function sysnum = findSys(Trials, sys)
% FINDSYS Find which system index corresponds to a system name
%
%   sysnum = findSys(Trials, sys)
%
%   Identifies which trials correspond to a specific system name
%   (recording tower). Handles legacy MT1/MT2 fields and modern
%   MT array structures.
%
%   Parameters:
%     Trials - Array of trial structs
%     sys    - System name string (e.g. 'LPPC_LPFC_modularV1')
%
%   Returns:
%     sysnum - Vector of system indices (0 if no match)
%
%   See also: trialNPSpike

nTr = length(Trials);
sysnum = zeros(1, nTr);

for iTr = 1:nTr
    if isfield(Trials(iTr), 'MT') && iscell(Trials(iTr).MT)
        for iMT = 1:length(Trials(iTr).MT)
            if ~isempty(regexp(Trials(iTr).MT{iMT}, ['^' sys], 'once'))
                sysnum(iTr) = iMT;
                break;
            end
        end
    elseif isfield(Trials(iTr), 'MT1')
        if ~isempty(regexp(Trials(iTr).MT1, ['^' sys], 'once'))
            sysnum(iTr) = 1;
        elseif isfield(Trials(iTr), 'MT2') && ~isempty(regexp(Trials(iTr).MT2, ['^' sys], 'once'))
            sysnum(iTr) = 2;
        end
    end
end

end
