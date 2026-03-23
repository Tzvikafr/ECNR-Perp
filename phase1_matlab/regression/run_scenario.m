function out = run_scenario(inputPath, opts)
%RUN_SCENARIO Execute one offline scenario (manifest or config path).

if nargin < 2
	opts = struct();
end

rootDir = fileparts(fileparts(mfilename('fullpath')));
workspaceRoot = fileparts(rootDir);
addpath(rootDir);
addpath(genpath(fullfile(rootDir, 'aec')));
addpath(genpath(fullfile(rootDir, 'beamformer')));
addpath(genpath(fullfile(rootDir, 'nr')));
addpath(genpath(fullfile(rootDir, 'metrics')));
addpath(genpath(fullfile(rootDir, 'io')));

inputObj = jsondecode(fileread(inputPath));

if isfield(inputObj, 'scenarios')
	error('run_scenario:InvalidInput', 'Input appears to be a suite file. Use run_regression_suite.');
end

if isfield(inputObj, 'config') && isfield(inputObj, 'mic_wav')
	scenario = inputObj;
	configPath = fullfile(workspaceRoot, scenario.config);
	micPath = fullfile(workspaceRoot, scenario.mic_wav);
	refPath = '';
	if isfield(scenario, 'ref_wav')
		refPath = fullfile(workspaceRoot, scenario.ref_wav);
	end
else
	% Backward-compatible synthetic mode when a config path is provided.
	scenario = struct('name', 'legacy_synthetic', 'config', inputPath);
	configPath = inputPath;
	micPath = '';
	refPath = '';
end

cfg = ecnr_load_config(configPath);

if isfield(opts, 'param_overrides') && isstruct(opts.param_overrides)
	keys = fieldnames(opts.param_overrides);
	for i = 1:numel(keys)
		cfg = set_struct_field(cfg, keys{i}, opts.param_overrides.(keys{i}));
	end
end

state = ecnr_init(cfg);
N = cfg.frame_size;

if ~isempty(micPath)
	[micAll, fsMic] = io_wav_read(micPath, cfg.sample_rate_hz, cfg.mic_count);
	if ~isempty(refPath)
		[refAll, fsRef] = io_wav_read(refPath, cfg.sample_rate_hz, 1);
		if fsMic ~= fsRef
			error('run_scenario:RateMismatch', 'Mic/reference sample rates mismatch after normalization.');
		end
	else
		refAll = [];
	end
else
	fsMic = cfg.sample_rate_hz;
	t = (0:N*30-1)' / fsMic;
	refAll = 0.25 * sin(2 * pi * 500 * t);
	voice = 0.1 * sin(2 * pi * 1200 * t);
	micMono = refAll + voice;
	micAll = repmat(micMono, 1, cfg.mic_count);
end

sampleCount = size(micAll, 1);
frameCount = floor(sampleCount / N);
if frameCount < 1
	error('run_scenario:TooShort', 'Input is shorter than one frame.');
end

yAll = zeros(frameCount * N, 1);
records = repmat(struct('erle_db', NaN, 'erle_inst_db', NaN, 'erle_window_db', NaN, ...
	'snr_in_db', NaN, 'snr_out_db', NaN, 'dtd_active', false, 'frame_index', uint64(0)), frameCount, 1);

for k = 1:frameCount
	idx = (k-1)*N + (1:N);
	micFrame = micAll(idx, :);

	if isempty(refAll)
		refFrame = io_reference_resolve(cfg, [], micFrame);
	else
		refFrame = io_reference_resolve(cfg, refAll(idx), micFrame);
	end

	[yFrame, state] = ecnr_process_frame(state, micFrame, refFrame);
	yAll(idx) = yFrame;
	records(k) = ecnr_get_metrics(state);
end

if isfield(scenario, 'output_wav')
	outWav = fullfile(workspaceRoot, scenario.output_wav);
	io_wav_write(outWav, yAll, cfg.sample_rate_hz);
end

if isfield(scenario, 'metrics_csv')
	outCsv = fullfile(workspaceRoot, scenario.metrics_csv);
	metrics_export_csv(records, outCsv);
end

metrics = ecnr_get_metrics(state);

out = struct();
out.name = scenario.name;
out.y = yAll;
out.metrics = metrics;
out.records = records;
out.frame_samples = numel(yAll);
out.frame_count = frameCount;
out.sample_rate_hz = cfg.sample_rate_hz;
end

function s = set_struct_field(s, dottedKey, value)
parts = strsplit(dottedKey, '.');
if numel(parts) == 1
	s.(parts{1}) = value;
	return;
end

head = parts{1};
tail = strjoin(parts(2:end), '.');
if ~isfield(s, head) || ~isstruct(s.(head))
	s.(head) = struct();
end
s.(head) = set_struct_field(s.(head), tail, value);
end
