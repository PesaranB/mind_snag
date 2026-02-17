function [X, Y] = getRasters(SpikeCell, bn)
% GETRASTERS Extract raster plot coordinates from spike cell array
%
%   [X, Y] = getRasters(SpikeCell, bn)
%
%   Parameters:
%     SpikeCell - Cell array of spike times per trial
%     bn        - [start, stop] time window in ms
%
%   Returns:
%     X - All spike times (for scatter plot x-coordinates)
%     Y - Trial indices (for scatter plot y-coordinates)

nTr = length(SpikeCell);
dT = 0.08;
Start = bn(1);

X = [];
Y = [];
for iTr = 1:nTr
    x = SpikeCell{iTr};
    if size(x,1) == 1; x = x'; end
    x = (x + Start)';
    y = ones(1, length(x)) * (iTr * dT);
    X = [X x];
    Y = [Y y];
end

end
