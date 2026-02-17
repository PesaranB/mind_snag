function [rate, nTr] = psth(spikecell, bn, smoothing, maxrate, marks, flag)
% PSTH Peri-stimulus time histogram from spike cell array
%
%   [rate, nTr] = psth(spikecell, bn, smoothing, maxrate, marks, flag)
%
%   Parameters:
%     spikecell - Cell array of spike times in ms (starting from 0)
%     bn        - [start, stop] time window in ms
%     smoothing - Gaussian smoothing std in ms (default: 50)
%     maxrate   - Max firing rate for display (default: 50)
%     marks     - Optional marker times for display
%     flag      - If 1, force plotting (default: 0)
%
%   Returns:
%     rate - Smoothed firing rate vector (spikes/s)
%     nTr  - Number of trials

if nargin < 3 || isempty(smoothing); smoothing = 50; end
if nargin < 4; maxrate = 50; end
if nargin < 5; marks = []; end
if nargin < 6; flag = 0; end

nTr = length(spikecell);
dT = maxrate ./ nTr;

Start = bn(1); Stop = bn(2);

XX = [];
Y = [];
for iTr = 1:nTr
    x = spikecell{iTr};
    if size(x,1) == 1; x = x'; end
    x = (x + Start)';
    y = ones(1, length(x)) * (iTr * dT);
    XX = [XX x];
    Y = [Y y];
end

if nargout == 0 || flag == 1
    if nTr > 5
        plot(XX, Y, 'r.', 'MarkerSize', 4);
    else
        plot(XX, Y, 'r.', 'MarkerSize', 10);
    end
end

if ~isempty(marks)
    hold on;
    plot(marks, [1:nTr] .* dT, 'k.', 'Markersize', 10)
end

Z = hist(XX, Start:Stop);
window = normpdf([-3*smoothing:3*smoothing], 0, smoothing);

rate = (1000 / nTr) * conv(Z, window);
rate = rate(3*smoothing + 1 : end - 3*smoothing);

if nargout == 0 || flag == 1
    hold on;
    plot(Start:Stop, rate, 'k', 'linewidth', 3);
    plot([0 0], [0 maxrate], 'b')
    axis([Start Stop 0 maxrate])
end

end
