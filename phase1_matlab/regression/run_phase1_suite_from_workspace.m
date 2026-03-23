function summary = run_phase1_suite_from_workspace()
%RUN_PHASE1_SUITE_FROM_WORKSPACE Generate assets, run suite, and print summary.

workspaceRoot = fileparts(fileparts(fileparts(mfilename('fullpath'))));
addpath(genpath(fullfile(workspaceRoot, 'phase1_matlab')));

generate_phase1_assets();

suitePath = fullfile(workspaceRoot, 'scenarios', 'phase1_suite.json');
summary = run_regression_suite(suitePath);

disp('Phase 1 suite summary:');
disp(summary);
end
