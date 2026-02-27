function p = resolve_path(data_root, template, vars)
% RESOLVE_PATH Substitute {key} placeholders in a path template.
%
%   p = resolve_path(data_root, template, vars)
%
%   Replaces {key} tokens in `template` with the corresponding field values
%   from the struct `vars`, then prepends `data_root`.
%
%   Parameters:
%     data_root - Root data directory (string)
%     template  - Path template with {key} placeholders (string)
%     vars      - Struct with field names matching template placeholders
%
%   Returns:
%     p - Full resolved path (string)
%
%   Example:
%     vars.day = '250224';
%     vars.rec = '007';
%     vars.tower = 'LPPC_LPFC_modularV1';
%     vars.np = 1;
%     vars.group_flag = 'Grouped';
%     p = resolve_path('/data', '{day}/{rec}/rec{rec}.{tower}.{np}.{group_flag}.NPclu.mat', vars);
%     % p = '/data/250224/007/rec007.LPPC_LPFC_modularV1.1.Grouped.NPclu.mat'
%
%   See also: mind_snag_config

result = template;
fields = fieldnames(vars);
for i = 1:length(fields)
    key = fields{i};
    val = vars.(key);
    if isnumeric(val)
        val = num2str(val);
    end
    result = strrep(result, ['{' key '}'], val);
end
p = fullfile(data_root, result);

end
