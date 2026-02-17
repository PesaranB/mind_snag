function params = loadParamsPy(filename)
% LOADPARAMSPY Load Kilosort/Phy params.py file into a MATLAB struct
%
%   params = loadParamsPy(filename)
%
%   Parses Python-style key=value parameter files (params.py) generated
%   by Kilosort and Phy.
%
%   Parameters:
%     filename - Path to params.py file
%
%   Returns:
%     params - Struct with parsed key-value pairs
%
%   See also: loadKSdir

params = struct();

fid = fopen(filename);
while ~feof(fid)
    line = fgetl(fid);
    if isempty(line) || line(1) == '#'
        continue;
    end
    tokens = strsplit(line, '=');
    if length(tokens) >= 2
        key = strtrim(tokens{1});
        val = strtrim(strjoin(tokens(2:end), '='));

        % Remove quotes
        val = strrep(val, '''', '');
        val = strrep(val, '"', '');

        % Try numeric conversion
        numVal = str2double(val);
        if ~isnan(numVal)
            params.(key) = numVal;
        elseif strcmp(val, 'True')
            params.(key) = true;
        elseif strcmp(val, 'False')
            params.(key) = false;
        else
            params.(key) = val;
        end
    end
end
fclose(fid);

end
