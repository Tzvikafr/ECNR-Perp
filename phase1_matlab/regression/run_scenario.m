function out = run_scenario(configPath)
%RUN_SCENARIO Execute one synthetic offline scenario.

rootDir = fileparts(fileparts(mfilename('fullpath')));
addpath(rootDir);
addpath(genpath(fullfile(rootDir, 'aec')));
addpath(genpath(fullfile(rootDir, 'beamformer')));
addpath(genpath(fullfile(rootDir, 'nr')));
addpath(genpath(fullfile(rootDir, 'metrics')));

cfg = ecnr_load_config(configPath);
state = ecnr_init(cfg);

N = cfg.frame.length_samples;
fs = cfg.sample_rate_hz;
t = (0:N-1)' / fs;

% Synthetic mic and reference signals for smoke testing.
ref = 0.3 * sin(2 * pi * 500 * t);
voice = 0.1 * sin(2 * pi * 1200 * t);
mic = ref + voice;
mic_frame = repmat(mic, 1, cfg.mic_count);

[y, state] = ecnr_process_frame(state, mic_frame, ref);
metrics = ecnr_get_metrics(state);

out = struct();
out.y = y;
out.metrics = metrics;
out.frame_samples = numel(y);
end
