function cfg = ecnr_load_config(configPath)
%ECNR_LOAD_CONFIG Load and minimally validate ECNR Phase 1 JSON config.

if nargin < 1 || isempty(configPath)
    error('ecnr_load_config:MissingPath', 'configPath is required.');
end

if ~isfile(configPath)
    error('ecnr_load_config:MissingFile', 'Config file not found: %s', configPath);
end

raw = fileread(configPath);
cfg = jsondecode(raw);

requiredFields = {'schema_version','mic_count','beamformer','aec','nr'};
for i = 1:numel(requiredFields)
    if ~isfield(cfg, requiredFields{i})
        error('ecnr_load_config:MissingField', 'Missing required field: %s', requiredFields{i});
    end
end

% Normalize sampling rate naming.
if isfield(cfg, 'sample_rate_hz')
    cfg.sampling_rate = cfg.sample_rate_hz;
elseif isfield(cfg, 'sampling_rate')
    cfg.sample_rate_hz = cfg.sampling_rate;
else
    error('ecnr_load_config:MissingField', 'Missing required field: sample_rate_hz or sampling_rate.');
end

if ~ismember(cfg.sampling_rate, [16000 48000])
    error('ecnr_load_config:InvalidSamplingRate', 'sample_rate_hz/sampling_rate must be 16000 or 48000.');
end

if ~ismember(cfg.mic_count, [1 2 4])
    error('ecnr_load_config:InvalidMicCount', 'mic_count must be 1, 2, or 4.');
end

% Normalize frame sizing.
if isfield(cfg, 'frame') && isfield(cfg.frame, 'length_samples')
    cfg.frame_size = cfg.frame.length_samples;
elseif isfield(cfg, 'frame_size')
    if ~isfield(cfg, 'frame')
        cfg.frame = struct();
    end
    cfg.frame.length_samples = cfg.frame_size;
else
    error('ecnr_load_config:MissingField', 'Missing required field: frame.length_samples or frame_size.');
end

if cfg.frame_size <= 0 || mod(cfg.frame_size, 1) ~= 0
    error('ecnr_load_config:InvalidFrameSize', 'frame.length_samples/frame_size must be a positive integer.');
end

% Normalize mode for top-level pipeline convenience.
if isfield(cfg.nr, 'mode')
    cfg.mode = cfg.nr.mode;
elseif isfield(cfg, 'mode')
    cfg.nr.mode = cfg.mode;
else
    cfg.mode = 'traditional';
    cfg.nr.mode = 'traditional';
end
end
