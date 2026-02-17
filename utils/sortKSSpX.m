function [sortedRT, sortedSpx] = sortKSSpX(RT, spX)
% SORTKSSP Sort spike rasters by reaction time
%
%   [sortedRT, sortedSpx] = sortKSSpX(RT, spX)
%
%   Parameters:
%     RT  - Vector of reaction times
%     spX - Cell array of spike times per trial
%
%   Returns:
%     sortedRT  - Sorted reaction times (ascending)
%     sortedSpx - Spike cell array sorted by RT

if ~isempty(RT)
    [sortedRT, sortRTind] = sort(RT, 'ascend');
    for i = 1:length(sortRTind)
        tmpInd = sortRTind(i);
        tmpSp = spX{tmpInd};
        sortedSpx{i,:} = tmpSp;
    end
else
    sortedRT = [];
    sortedSpx = spX;
end

end
