function NPelec = getNP_chanDepthInfo(day, rec, npNum, tower, data_root)
% GETNP_CHANDEPTHINFO Get channel depth and position info for a Neuropixel probe
%
%   NPelec = getNP_chanDepthInfo(day, rec, npNum, tower, data_root)
%
%   Parameters:
%     day       - Recording date (YYMMDD string)
%     rec       - Recording number (string)
%     npNum     - Probe number (1 or 2)
%     tower     - Recording setup name
%     data_root - Root data directory (optional, uses global MONKEYDIR if omitted)
%
%   Returns:
%     NPelec - Struct with fields: ChanId, depth, row, col, x_coord, y_coord, elecNum

if nargin < 5 || isempty(data_root)
    global MONKEYDIR
    data_root = MONKEYDIR;
end

edf = loadExperiment(day, rec);

names = {edf.hardware.microdrive.name};
driveInd = ismember(names, tower);

npInfo = edf.hardware.microdrive(driveInd).electrodes;

channel_info_file = fullfile(data_root, day, rec, ...
    ['rec' num2str(rec) '.' tower '.' num2str(npNum) '.channel_info.mat']);
chanInfo = load(channel_info_file);
chanInfo = chanInfo.channel_info;
elecNum = [chanInfo.electrode];

thisNP_info = npInfo(elecNum);
thisNP_pos = [thisNP_info.position];

NPelec = [];
NPelec.ChanId = [thisNP_info.channelid];
if isfield(thisNP_pos, 'depth')
    NPelec.depth = [thisNP_pos.depth];
end
NPelec.row = [thisNP_pos.within_probe_row];
NPelec.col = [thisNP_pos.within_probe_col];
NPelec.x_coord = [thisNP_pos.within_probe_x];
NPelec.y_coord = [thisNP_pos.within_probe_y];
NPelec.elecNum = elecNum;

end
