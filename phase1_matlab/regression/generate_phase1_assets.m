function generate_phase1_assets()
%GENERATE_PHASE1_ASSETS Create deterministic WAV assets for offline Phase 1 regression.

rootDir = fileparts(fileparts(mfilename('fullpath')));
workspaceRoot = fileparts(rootDir);
assetsDir = fullfile(workspaceRoot, 'scenarios', 'assets');
if ~isfolder(assetsDir)
    mkdir(assetsDir);
end

cfg = ecnr_load_config(fullfile(workspaceRoot, 'configs', 'phase1_default.json'));
fs = cfg.sample_rate_hz;
durSec = 4;
t = (0:durSec * fs - 1)' / fs;

ref = 0.28 * sin(2 * pi * 450 * t) + 0.12 * sin(2 * pi * 820 * t);
voice = 0.08 * sin(2 * pi * 1350 * t) + 0.03 * randn(size(t));
nearNoise = 0.02 * randn(size(t));

mic1 = ref + voice + nearNoise;
mic2 = 0.9 * ref + 1.05 * voice + 0.02 * randn(size(t));
mic = [mic1 mic2];

audiowrite(fullfile(assetsDir, 'phase1_ref.wav'), ref, fs);
audiowrite(fullfile(assetsDir, 'phase1_mic.wav'), mic, fs);
end
