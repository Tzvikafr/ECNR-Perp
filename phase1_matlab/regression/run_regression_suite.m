function summary = run_regression_suite(inputPath)
%RUN_REGRESSION_SUITE Run one scenario or a full suite manifest.

rootDir = fileparts(fileparts(mfilename('fullpath')));
workspaceRoot = fileparts(rootDir);

obj = jsondecode(fileread(inputPath));

if ~isfield(obj, 'scenarios')
    result = run_scenario(inputPath);

    summary = struct();
    summary.pass = isstruct(result.metrics) && isfield(result.metrics, 'erle_db');
    summary.frame_samples = result.frame_samples;
    summary.metrics = result.metrics;
    summary.results = result;
    if ~summary.pass
        error('run_regression_suite:Failed', 'Smoke regression failed.');
    end
    return;
end

scenarioCount = numel(obj.scenarios);
results = repmat(struct('name', '', 'pass', false, 'last_metrics', struct(), 'frame_count', 0), scenarioCount, 1);

for i = 1:scenarioCount
    scenarioPath = fullfile(workspaceRoot, obj.scenarios{i});
    r = run_scenario(scenarioPath);
    results(i).name = r.name;
    results(i).pass = isstruct(r.metrics) && isfield(r.metrics, 'erle_db');
    results(i).last_metrics = r.metrics;
    results(i).frame_count = r.frame_count;
end

summary = struct();
summary.results = results;
summary.scenario_count = scenarioCount;
summary.pass = all([results.pass]);

if isfield(obj, 'baseline_compare') && isstruct(obj.baseline_compare)
    cmp = obj.baseline_compare;
    currentCsv = fullfile(workspaceRoot, cmp.current_csv);
    baselineCsv = fullfile(workspaceRoot, cmp.baseline_csv);
    thresholds = cmp.thresholds;
    summary.baseline = compare_metrics_csv(currentCsv, baselineCsv, thresholds);
    summary.pass = summary.pass && summary.baseline.pass;
end

if ~summary.pass
    error('run_regression_suite:Failed', 'Regression suite failed.');
end
end

function out = compare_metrics_csv(currentCsv, baselineCsv, thresholds)
if ~isfile(currentCsv)
    error('run_regression_suite:MissingCurrentCsv', 'Missing current CSV: %s', currentCsv);
end
if ~isfile(baselineCsv)
    error('run_regression_suite:MissingBaselineCsv', 'Missing baseline CSV: %s', baselineCsv);
end

Tcur = readtable(currentCsv);
Tbase = readtable(baselineCsv);

out = struct();
out.pass = true;
out.checks = struct();

if isfield(thresholds, 'erle_window_db_min_delta') && ismember('erle_window_db', Tcur.Properties.VariableNames) && ismember('erle_window_db', Tbase.Properties.VariableNames)
    d = mean(Tcur.erle_window_db, 'omitnan') - mean(Tbase.erle_window_db, 'omitnan');
    out.checks.erle_window_db_delta = d;
    out.pass = out.pass && (d >= thresholds.erle_window_db_min_delta);
end

if isfield(thresholds, 'snr_out_db_min_delta') && ismember('snr_out_db', Tcur.Properties.VariableNames) && ismember('snr_out_db', Tbase.Properties.VariableNames)
    d = mean(Tcur.snr_out_db, 'omitnan') - mean(Tbase.snr_out_db, 'omitnan');
    out.checks.snr_out_db_delta = d;
    out.pass = out.pass && (d >= thresholds.snr_out_db_min_delta);
end
end
