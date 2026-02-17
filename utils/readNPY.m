function data = readNPY(filename)
% READNPY Read NumPy .npy binary files into MATLAB
%
%   data = readNPY(filename)
%
%   Reads N-D arrays from NPY format files. Only supports a subset of
%   possible NPY files (numeric arrays of standard data types).
%
%   Parameters:
%     filename - Path to .npy file
%
%   Returns:
%     data - MATLAB array with the data from the NPY file
%
%   See also: readNPYheader

[shape, dataType, fortranOrder, littleEndian, totalHeaderLength, ~] = readNPYheader(filename);

if littleEndian
    fid = fopen(filename, 'r', 'l');
else
    fid = fopen(filename, 'r', 'b');
end

try
    [~] = fread(fid, totalHeaderLength, 'uint8');

    % read the data
    data = fread(fid, prod(shape), [dataType '=>' dataType]);

    if length(shape)>1 && ~fortranOrder
        data = reshape(data, shape(end:-1:1));
        data = permute(data, [length(shape):-1:1]);
    elseif length(shape)>1
        data = reshape(data, shape);
    end

    fclose(fid);

catch me
    fclose(fid);
    rethrow(me);
end

end
