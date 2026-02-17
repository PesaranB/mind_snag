function Recs = getRec(Trials)
% GETREC Extract recording identifiers from Trials structure
%
%   Recs = getRec(Trials)
%
%   Parameters:
%     Trials - Array of trial structs, each with a .Rec field
%
%   Returns:
%     Recs - Cell array of recording identifiers
%
%   See also: trialNPSpike

Recs = {Trials.Rec};

end
