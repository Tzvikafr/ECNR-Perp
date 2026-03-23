function ecnr_gui_launch()
%ECNR_GUI_LAUNCH Launch Phase 1 MATLAB tuning GUI for offline scenarios.

workspaceRoot = fileparts(fileparts(fileparts(mfilename('fullpath'))));
addpath(genpath(fullfile(workspaceRoot, 'phase1_matlab')));

fig = uifigure('Name', 'ECNR Phase 1 Tuning Tool', 'Position', [100 100 1120 680]);
g = uigridlayout(fig, [6 4]);
g.RowHeight = {34, 34, 34, 34, '1x', '1x'};
g.ColumnWidth = {260, 260, '1x', '1x'};

uilabel(g, 'Text', 'Scenario JSON');
scenarioEdit = uieditfield(g, 'text', 'Value', 'scenarios/phase1_offline_wav.json');
scenarioEdit.Layout.Row = 1;
scenarioEdit.Layout.Column = [2 3];

browseBtn = uibutton(g, 'Text', 'Browse...');
browseBtn.Layout.Row = 1;
browseBtn.Layout.Column = 4;

uilabel(g, 'Text', 'AEC Step Size');
stepField = uieditfield(g, 'numeric', 'Limits', [0.001 1], 'Value', 0.1);
stepField.Layout.Row = 2;
stepField.Layout.Column = 2;

uilabel(g, 'Text', 'NR Aggressiveness (dB)');
nrField = uieditfield(g, 'numeric', 'Limits', [0 24], 'Value', 8);
nrField.Layout.Row = 2;
nrField.Layout.Column = 3;

runBtn = uibutton(g, 'Text', 'Run Scenario');
runBtn.Layout.Row = 2;
runBtn.Layout.Column = 4;

metricsArea = uitextarea(g, 'Editable', 'off');
metricsArea.Layout.Row = [3 4];
metricsArea.Layout.Column = [1 2];
metricsArea.Value = {'Metrics will appear here after run.'};

outputLabel = uilabel(g, 'Text', 'Output: idle');
outputLabel.Layout.Row = [3 4];
outputLabel.Layout.Column = [3 4];

axWave = uiaxes(g);
axWave.Layout.Row = 5;
axWave.Layout.Column = [1 4];
title(axWave, 'Output Waveform (First 2000 Samples)');
xlabel(axWave, 'Sample');
ylabel(axWave, 'Amplitude');

axErle = uiaxes(g);
axErle.Layout.Row = 6;
axErle.Layout.Column = [1 4];
title(axErle, 'ERLE Over Frames');
xlabel(axErle, 'Frame');
ylabel(axErle, 'ERLE (dB)');

browseBtn.ButtonPushedFcn = @onBrowse;
runBtn.ButtonPushedFcn = @onRun;

    function onBrowse(~, ~)
        [file, path] = uigetfile(fullfile(workspaceRoot, 'scenarios', '*.json'), 'Select Scenario');
        if isequal(file, 0)
            return;
        end
        full = fullfile(path, file);
        rel = erase(full, [workspaceRoot filesep]);
        scenarioEdit.Value = strrep(rel, '\\', '/');
    end

    function onRun(~, ~)
        try
            drawnow;
            outputLabel.Text = 'Output: running...';

            scenarioPath = fullfile(workspaceRoot, scenarioEdit.Value);
            if ~isfile(scenarioPath)
                error('ecnr_gui_launch:MissingScenario', 'Scenario file not found: %s', scenarioPath);
            end

            opts = struct();
            opts.param_overrides = struct();
            opts.param_overrides.('aec.step_size') = stepField.Value;
            opts.param_overrides.('nr.aggressiveness_db') = nrField.Value;

            result = run_scenario(scenarioPath, opts);
            renderResult(result);

            outputLabel.Text = sprintf('Output: done (%d frames)', result.frame_count);
        catch err
            outputLabel.Text = 'Output: failed';
            uialert(fig, err.message, 'Scenario Failed');
        end
    end

    function renderResult(result)
        m = result.metrics;
        lines = {
            sprintf('ERLE (inst): %.2f dB', m.erle_inst_db),
            sprintf('ERLE (window): %.2f dB', m.erle_window_db),
            sprintf('SNR in: %.2f dB', m.snr_in_db),
            sprintf('SNR out: %.2f dB', m.snr_out_db),
            sprintf('DTD active: %d', logical(m.dtd_active)),
            sprintf('Frame index: %d', m.frame_index)
        };
        metricsArea.Value = lines;

        y = result.y;
        showN = min(numel(y), 2000);
        plot(axWave, 1:showN, y(1:showN));

        erleSeries = [result.records.erle_window_db];
        plot(axErle, 1:numel(erleSeries), erleSeries, 'LineWidth', 1.2);
    end
end
