function [arrayShape, dataType, fortranOrder, littleEndian, totalHeaderLength, npyVersion] = readNPYheader(filename)
% READNPYHEADER Parse the header of a NumPy .npy file
%
%   [shape, dtype, fortranOrder, littleEndian, headerLen, ver] = readNPYheader(filename)
%
%   Parameters:
%     filename - Path to .npy file
%
%   Returns:
%     arrayShape       - Array dimensions
%     dataType         - MATLAB data type string
%     fortranOrder     - true if Fortran (column-major) order
%     littleEndian     - true if little-endian byte order
%     totalHeaderLength - Total bytes in the header
%     npyVersion       - NPY format version [major, minor]
%
%   See also: readNPY

fid = fopen(filename);

% verify magic number
magicNumber = fread(fid, [1 6], 'uint8');
expectedMagic = [147 78 85 77 80 89]; % \x93NUMPY
assert(isequal(magicNumber, expectedMagic), ...
    'readNPY:badMagic', 'File is not a valid NPY file: %s', filename);

npyVersion = fread(fid, [1 2], 'uint8');

if npyVersion(1) == 1
    headerLength = fread(fid, [1 1], 'uint16');
elseif npyVersion(1) >= 2
    headerLength = fread(fid, [1 1], 'uint32');
end

totalHeaderLength = 6 + 2 + 2 * npyVersion(1) + headerLength;

arrayFormat = fread(fid, [1 headerLength], 'char=>char');

fclose(fid);

% parse the header dictionary
r = regexp(arrayFormat, '''descr''\s*:\s*''([^'']+)''', 'tokens');
if ~isempty(r)
    dtStr = r{1}{1};
else
    error('readNPYheader:noDtype', 'Could not parse dtype from header');
end

littleEndian = dtStr(1) == '<' || dtStr(1) == '|';

switch dtStr(2:end)
    case 'f4'; dataType = 'single';
    case 'f8'; dataType = 'double';
    case 'i1'; dataType = 'int8';
    case 'i2'; dataType = 'int16';
    case 'i4'; dataType = 'int32';
    case 'i8'; dataType = 'int64';
    case 'u1'; dataType = 'uint8';
    case 'u2'; dataType = 'uint16';
    case 'u4'; dataType = 'uint32';
    case 'u8'; dataType = 'uint64';
    case 'b1'; dataType = 'logical';
    otherwise; error('readNPYheader:unsupportedDtype', 'Unsupported dtype: %s', dtStr);
end

r = regexp(arrayFormat, '''fortran_order''\s*:\s*(True|False)', 'tokens');
if ~isempty(r)
    fortranOrder = strcmp(r{1}{1}, 'True');
else
    fortranOrder = false;
end

r = regexp(arrayFormat, '''shape''\s*:\s*\(([^\)]*)\)', 'tokens');
if ~isempty(r)
    shapeStr = r{1}{1};
    shapeStr = strrep(shapeStr, ',', ' ');
    arrayShape = str2num(shapeStr); %#ok<ST2NM>
    if isempty(arrayShape)
        arrayShape = 1;
    end
else
    error('readNPYheader:noShape', 'Could not parse shape from header');
end

end
