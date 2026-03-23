function summary = run_regression_suite(configPath)
%RUN_REGRESSION_SUITE Run minimal regression smoke suite.

result = run_scenario(configPath);

summary = struct();
summary.pass = isstruct(result.metrics) && isfield(result.metrics, 'erle_db');
summary.frame_samples = result.frame_samples;
summary.metrics = result.metrics;

if ~summary.pass
    error('run_regression_suite:Failed', 'Smoke regression failed.');
end
end
