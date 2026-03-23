function freeze_phase1_baseline()
%FREEZE_PHASE1_BASELINE Regenerate and freeze baseline CSV from current implementation.

workspaceRoot = fileparts(fileparts(fileparts(mfilename('fullpath'))));
addpath(genpath(fullfile(workspaceRoot, 'phase1_matlab')));

generate_phase1_assets();

scenarioPath = fullfile(workspaceRoot, 'scenarios', 'phase1_offline_wav.json');
run_scenario(scenarioPath);

src = fullfile(workspaceRoot, 'metrics_baselines', 'phase1_offline_current.csv');
dst = fullfile(workspaceRoot, 'metrics_baselines', 'phase1_offline_baseline.csv');
if ~isfile(src)
    error('freeze_phase1_baseline:MissingCurrent', 'Current metrics CSV was not created.');
end
copyfile(src, dst);

fprintf('Baseline updated: %s\n', dst);
end
