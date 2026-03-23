function summary = run_smoke_from_workspace()
%RUN_SMOKE_FROM_WORKSPACE Convenience entrypoint for workspace smoke test.

workspaceRoot = fileparts(fileparts(fileparts(mfilename('fullpath'))));
configPath = fullfile(workspaceRoot, 'configs', 'phase1_default.json');
summary = run_regression_suite(configPath);

disp('Smoke summary:');
disp(summary);
end
