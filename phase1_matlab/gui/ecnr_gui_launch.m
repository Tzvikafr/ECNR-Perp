function ecnr_gui_launch()
%ECNR_GUI_LAUNCH Launch Phase 1 MATLAB tuning GUI for offline scenarios.

workspaceRoot = fileparts(fileparts(fileparts(mfilename('fullpath'))));
addpath(genpath(fullfile(workspaceRoot, 'phase1_matlab')));

fig = uifigure('Name', 'ECNR Phase 1 Tuning Tool', 'Position', [80 60 1480 860]);
outer = uigridlayout(fig, [1 2]);
outer.ColumnWidth = {460, '1x'};
outer.RowHeight = {'1x'};

leftPanel = uipanel(outer, 'Title', 'Controls');
leftPanel.Layout.Row = 1;
leftPanel.Layout.Column = 1;
leftGrid = uigridlayout(leftPanel, [2 1]);
leftGrid.RowHeight = {36, '1x'};
leftGrid.ColumnWidth = {'1x'};

statusLabel = uilabel(leftGrid, 'Text', 'Status: idle');
statusLabel.Layout.Row = 1;

tabs = uitabgroup(leftGrid);
tabs.Layout.Row = 2;

inputTab = uitab(tabs, 'Title', 'Input');
modulesTab = uitab(tabs, 'Title', 'Modules');
tuningTab = uitab(tabs, 'Title', 'Tuning');

inputGrid = uigridlayout(inputTab, [8 3]);
inputGrid.RowHeight = repmat({30}, 1, 8);
inputGrid.ColumnWidth = {120, '1x', 90};

uilabel(inputGrid, 'Text', 'Input Mode');
inputModeDrop = uidropdown(inputGrid, 'Items', {'Scenario JSON', 'Direct WAV'}, 'Value', 'Scenario JSON');
inputModeDrop.Layout.Row = 1;
inputModeDrop.Layout.Column = [2 3];

uilabel(inputGrid, 'Text', 'Scenario JSON');
scenarioEdit = uieditfield(inputGrid, 'text', 'Value', 'scenarios/phase1_offline_wav.json');
scenarioEdit.Layout.Row = 2;
scenarioEdit.Layout.Column = 2;
scenarioBrowseBtn = uibutton(inputGrid, 'Text', 'Browse...');
scenarioBrowseBtn.Layout.Row = 2;
scenarioBrowseBtn.Layout.Column = 3;

uilabel(inputGrid, 'Text', 'Base Config');
configEdit = uieditfield(inputGrid, 'text', 'Value', 'configs/phase1_default.json');
configEdit.Layout.Row = 3;
configEdit.Layout.Column = 2;
configBrowseBtn = uibutton(inputGrid, 'Text', 'Browse...');
configBrowseBtn.Layout.Row = 3;
configBrowseBtn.Layout.Column = 3;

uilabel(inputGrid, 'Text', 'Mic WAV');
micEdit = uieditfield(inputGrid, 'text', 'Value', 'scenarios/assets/phase1_mic.wav');
micEdit.Layout.Row = 4;
micEdit.Layout.Column = 2;
micBrowseBtn = uibutton(inputGrid, 'Text', 'Browse...');
micBrowseBtn.Layout.Row = 4;
micBrowseBtn.Layout.Column = 3;

uilabel(inputGrid, 'Text', 'Ref WAV');
refEdit = uieditfield(inputGrid, 'text', 'Value', 'scenarios/assets/phase1_ref.wav');
refEdit.Layout.Row = 5;
refEdit.Layout.Column = 2;
refBrowseBtn = uibutton(inputGrid, 'Text', 'Browse...');
refBrowseBtn.Layout.Row = 5;
refBrowseBtn.Layout.Column = 3;

uilabel(inputGrid, 'Text', 'Output WAV');
outputWavEdit = uieditfield(inputGrid, 'text', 'Value', 'scenarios/results/gui_output.wav');
outputWavEdit.Layout.Row = 6;
outputWavEdit.Layout.Column = 2;
outputWavBrowseBtn = uibutton(inputGrid, 'Text', 'Browse...');
outputWavBrowseBtn.Layout.Row = 6;
outputWavBrowseBtn.Layout.Column = 3;

uilabel(inputGrid, 'Text', 'Metrics CSV');
metricsCsvEdit = uieditfield(inputGrid, 'text', 'Value', 'metrics_baselines/gui_metrics.csv');
metricsCsvEdit.Layout.Row = 7;
metricsCsvEdit.Layout.Column = 2;
metricsCsvBrowseBtn = uibutton(inputGrid, 'Text', 'Browse...');
metricsCsvBrowseBtn.Layout.Row = 7;
metricsCsvBrowseBtn.Layout.Column = 3;

inputHint = uitextarea(inputGrid, 'Editable', 'off');
inputHint.Layout.Row = 8;
inputHint.Layout.Column = [1 3];
inputHint.Value = {'Scenario JSON mode reads paths from manifest; Direct WAV mode uses files chosen below and the selected Base Config.'};

modulesGrid = uigridlayout(modulesTab, [8 2]);
modulesGrid.RowHeight = repmat({30}, 1, 8);
modulesGrid.ColumnWidth = {180, '1x'};

beamEnable = uicheckbox(modulesGrid, 'Text', 'Beamformer Enabled', 'Value', true);
beamEnable.Layout.Row = 1;
beamEnable.Layout.Column = 1;
uilabel(modulesGrid, 'Text', 'Beamformer Algorithm');
beamAlgo = uidropdown(modulesGrid, 'Items', {'off', 'das'}, 'Value', 'das');
beamAlgo.Layout.Row = 2;
beamAlgo.Layout.Column = 2;

aecEnable = uicheckbox(modulesGrid, 'Text', 'AEC Enabled', 'Value', true);
aecEnable.Layout.Row = 3;
aecEnable.Layout.Column = 1;
uilabel(modulesGrid, 'Text', 'AEC Algorithm');
aecAlgo = uidropdown(modulesGrid, 'Items', {'bypass', 'nlms'}, 'Value', 'nlms');
aecAlgo.Layout.Row = 4;
aecAlgo.Layout.Column = 2;

nrEnable = uicheckbox(modulesGrid, 'Text', 'NR Enabled', 'Value', true);
nrEnable.Layout.Row = 5;
nrEnable.Layout.Column = 1;
uilabel(modulesGrid, 'Text', 'NR Algorithm');
nrAlgo = uidropdown(modulesGrid, 'Items', {'bypass', 'traditional', 'hybrid'}, 'Value', 'traditional');
nrAlgo.Layout.Row = 6;
nrAlgo.Layout.Column = 2;

uilabel(modulesGrid, 'Text', 'Reference Source');
refSource = uidropdown(modulesGrid, 'Items', {'file', 'capture_channel', 'loopback'}, 'Value', 'file');
refSource.Layout.Row = 7;
refSource.Layout.Column = 2;

moduleHint = uitextarea(modulesGrid, 'Editable', 'off');
moduleHint.Layout.Row = 8;
moduleHint.Layout.Column = [1 2];
moduleHint.Value = {'Hybrid is a guarded placeholder in Phase 1 and currently behaves as residual passthrough.'};

tuningGrid = uigridlayout(tuningTab, [12 2]);
tuningGrid.RowHeight = repmat({30}, 1, 12);
tuningGrid.ColumnWidth = {210, '1x'};

uilabel(tuningGrid, 'Text', 'Sample Rate (restart)');
sampleRateField = uidropdown(tuningGrid, 'Items', {'16000', '48000'}, 'Value', '16000');
sampleRateField.Layout.Row = 1;
sampleRateField.Layout.Column = 2;

uilabel(tuningGrid, 'Text', 'Frame Size Samples (restart)');
frameSizeField = uieditfield(tuningGrid, 'numeric', 'Limits', [80 2048], 'RoundFractionalValues', true, 'Value', 320);
frameSizeField.Layout.Row = 2;
frameSizeField.Layout.Column = 2;

uilabel(tuningGrid, 'Text', 'Mic Count (restart)');
micCountField = uidropdown(tuningGrid, 'Items', {'1', '2', '4'}, 'Value', '2');
micCountField.Layout.Row = 3;
micCountField.Layout.Column = 2;

uilabel(tuningGrid, 'Text', 'Ref Delay Samples (hot)');
refDelayField = uieditfield(tuningGrid, 'numeric', 'Value', 0, 'RoundFractionalValues', true);
refDelayField.Layout.Row = 4;
refDelayField.Layout.Column = 2;

uilabel(tuningGrid, 'Text', 'AEC Filter Length (restart)');
aecFilterField = uieditfield(tuningGrid, 'numeric', 'Limits', [16 4096], 'RoundFractionalValues', true, 'Value', 128);
aecFilterField.Layout.Row = 5;
aecFilterField.Layout.Column = 2;

uilabel(tuningGrid, 'Text', 'AEC Step Size (hot)');
aecStepField = uieditfield(tuningGrid, 'numeric', 'Limits', [0.001 1], 'Value', 0.1);
aecStepField.Layout.Row = 6;
aecStepField.Layout.Column = 2;

uilabel(tuningGrid, 'Text', 'AEC Regularization (hot)');
aecRegField = uieditfield(tuningGrid, 'numeric', 'Limits', [1e-12 1], 'Value', 1e-6);
aecRegField.Layout.Row = 7;
aecRegField.Layout.Column = 2;

uilabel(tuningGrid, 'Text', 'DTD Threshold dB (hot)');
dtdField = uieditfield(tuningGrid, 'numeric', 'Limits', [-20 40], 'Value', 6);
dtdField.Layout.Row = 8;
dtdField.Layout.Column = 2;

uilabel(tuningGrid, 'Text', 'ERLE Window Frames (restart)');
erleWindowField = uieditfield(tuningGrid, 'numeric', 'Limits', [1 200], 'RoundFractionalValues', true, 'Value', 25);
erleWindowField.Layout.Row = 9;
erleWindowField.Layout.Column = 2;

uilabel(tuningGrid, 'Text', 'NR Aggressiveness dB (hot)');
nrAggField = uieditfield(tuningGrid, 'numeric', 'Limits', [0 40], 'Value', 8);
nrAggField.Layout.Row = 10;
nrAggField.Layout.Column = 2;

reinitBtn = uibutton(tuningGrid, 'Text', 'Reinitialize');
reinitBtn.Layout.Row = 11;
reinitBtn.Layout.Column = 1;

runBtn = uibutton(tuningGrid, 'Text', 'Run Scenario');
runBtn.Layout.Row = 11;
runBtn.Layout.Column = 2;

exportBtn = uibutton(tuningGrid, 'Text', 'Export Metrics CSV');
exportBtn.Layout.Row = 12;
exportBtn.Layout.Column = [1 2];

rightPanel = uipanel(outer, 'Title', 'Metrics and Plots');
rightPanel.Layout.Row = 1;
rightPanel.Layout.Column = 2;
rightGrid = uigridlayout(rightPanel, [8 2]);
rightGrid.RowHeight = {34, 120, 140, '1x', '1x', '1x', '1x', '1x'};
rightGrid.ColumnWidth = {'1x', '1x'};

headerLabel = uilabel(rightGrid, 'Text', 'Latest run: none');
headerLabel.Layout.Row = 1;
headerLabel.Layout.Column = [1 2];

metricsArea = uitextarea(rightGrid, 'Editable', 'off');
metricsArea.Layout.Row = 2;
metricsArea.Layout.Column = 1;
metricsArea.Value = {'Metrics will appear here after run.'};

summaryTable = uitable(rightGrid, 'ColumnName', {'Metric', 'Value'}, 'Data', cell(0, 2));
summaryTable.Layout.Row = 2;
summaryTable.Layout.Column = 2;

runTable = uitable(rightGrid, 'ColumnName', {'Run', 'Frames', 'ERLE Win', 'SNR Out', 'Convergence s'});
runTable.Layout.Row = 3;
runTable.Layout.Column = [1 2];
runTable.Data = cell(0, 5);

axWave = uiaxes(rightGrid);
axWave.Layout.Row = 4;
axWave.Layout.Column = [1 2];
title(axWave, 'Output Waveform (First 2000 Samples)');
xlabel(axWave, 'Sample');
ylabel(axWave, 'Amplitude');

axErle = uiaxes(rightGrid);
axErle.Layout.Row = 5;
axErle.Layout.Column = [1 2];
title(axErle, 'ERLE Window Over Frames');
xlabel(axErle, 'Frame');
ylabel(axErle, 'ERLE (dB)');

axTrend = uiaxes(rightGrid);
axTrend.Layout.Row = 6;
axTrend.Layout.Column = [1 2];
title(axTrend, 'SNR Out and DTD Timeline');
xlabel(axTrend, 'Frame');
ylabel(axTrend, 'Value');

axSpectrogramWith = uiaxes(rightGrid);
axSpectrogramWith.Layout.Row = 7;
axSpectrogramWith.Layout.Column = 1;
title(axSpectrogramWith, 'Spectrogram (With Algorithm)');
xlabel(axSpectrogramWith, 'Time (s)');
ylabel(axSpectrogramWith, 'Frequency (Hz)');

axSpectrogramWithout = uiaxes(rightGrid);
axSpectrogramWithout.Layout.Row = 7;
axSpectrogramWithout.Layout.Column = 2;
title(axSpectrogramWithout, 'Spectrogram (Modules Off)');
xlabel(axSpectrogramWithout, 'Time (s)');
ylabel(axSpectrogramWithout, 'Frequency (Hz)');

axSpectrogramDiff = uiaxes(rightGrid);
axSpectrogramDiff.Layout.Row = 8;
axSpectrogramDiff.Layout.Column = [1 2];
title(axSpectrogramDiff, 'Spectrogram Difference (dB) - Algorithm Effect');
xlabel(axSpectrogramDiff, 'Time (s)');
ylabel(axSpectrogramDiff, 'Frequency (Hz)');

lastResult = [];
runRows = cell(0, 5);
restartSnapshot = struct();
restartDirty = false;

scenarioBrowseBtn.ButtonPushedFcn = @(~, ~) browseInput(scenarioEdit, fullfile(workspaceRoot, 'scenarios', '*.json'), false);
configBrowseBtn.ButtonPushedFcn = @(~, ~) browseInput(configEdit, fullfile(workspaceRoot, 'configs', '*.json'), false);
micBrowseBtn.ButtonPushedFcn = @(~, ~) browseInput(micEdit, fullfile(workspaceRoot, '*.wav'), false);
refBrowseBtn.ButtonPushedFcn = @(~, ~) browseInput(refEdit, fullfile(workspaceRoot, '*.wav'), false);
outputWavBrowseBtn.ButtonPushedFcn = @(~, ~) browseInput(outputWavEdit, fullfile(workspaceRoot, '*.wav'), true);
metricsCsvBrowseBtn.ButtonPushedFcn = @(~, ~) browseInput(metricsCsvEdit, fullfile(workspaceRoot, '*.csv'), true);
inputModeDrop.ValueChangedFcn = @onInputModeChanged;
scenarioEdit.ValueChangedFcn = @onScenarioChanged;
reinitBtn.ButtonPushedFcn = @onReinitialize;
runBtn.ButtonPushedFcn = @onRun;
exportBtn.ButtonPushedFcn = @onExportMetrics;

restartControls = [sampleRateField, frameSizeField, micCountField, aecFilterField, erleWindowField, beamAlgo, aecAlgo, nrAlgo];
for i = 1:numel(restartControls)
    restartControls(i).ValueChangedFcn = @onRestartControlChanged;
end

hotControls = [beamEnable, aecEnable, nrEnable, refSource, refDelayField, aecStepField, aecRegField, dtdField, nrAggField];
for i = 1:numel(hotControls)
    hotControls(i).ValueChangedFcn = @onHotControlChanged;
end

loadScenarioConfig();
syncInputMode();
captureRestartSnapshot();

    function browseInput(targetField, pattern, saveMode)
        if nargin < 3
            saveMode = false;
        end

        if saveMode
            [file, path] = uiputfile(pattern, 'Select Output File');
        else
            [file, path] = uigetfile(pattern, 'Select File');
        end

        if isequal(file, 0)
            return;
        end

        fullPath = fullfile(path, file);
        if startsWith(lower(fullPath), lower(workspaceRoot))
            rel = erase(fullPath, [workspaceRoot filesep]);
            targetField.Value = strrep(rel, '\', '/');
        else
            targetField.Value = fullPath;
        end
    end

    function onInputModeChanged(~, ~)
        syncInputMode();
        updateStatus('Input mode updated.');
    end

    function syncInputMode()
        isScenario = strcmp(inputModeDrop.Value, 'Scenario JSON');
        scenarioEdit.Editable = isScenario;
        scenarioBrowseBtn.Enable = tf(isScenario);
        micEdit.Editable = ~isScenario;
        micBrowseBtn.Enable = tf(~isScenario);
        refEdit.Editable = ~isScenario;
        refBrowseBtn.Enable = tf(~isScenario);
    end

    function onScenarioChanged(~, ~)
        if strcmp(inputModeDrop.Value, 'Scenario JSON')
            loadScenarioConfig();
            updateStatus('Scenario loaded into controls.');
        end
    end

    function loadScenarioConfig()
        scenarioPath = resolveUiPath(scenarioEdit.Value);
        if ~isfile(scenarioPath)
            updateStatus('Scenario path not found. Using current control values.');
            return;
        end

        scenarioObj = jsondecode(fileread(scenarioPath));
        if isfield(scenarioObj, 'config')
            configEdit.Value = normalizeToWorkspace(scenarioObj.config);
        end
        if isfield(scenarioObj, 'mic_wav')
            micEdit.Value = normalizeToWorkspace(scenarioObj.mic_wav);
        end
        if isfield(scenarioObj, 'ref_wav')
            refEdit.Value = normalizeToWorkspace(scenarioObj.ref_wav);
        end
        if isfield(scenarioObj, 'output_wav')
            outputWavEdit.Value = normalizeToWorkspace(scenarioObj.output_wav);
        end
        if isfield(scenarioObj, 'metrics_csv')
            metricsCsvEdit.Value = normalizeToWorkspace(scenarioObj.metrics_csv);
        end

        cfgPath = resolveUiPath(configEdit.Value);
        if isfile(cfgPath)
            applyConfigToControls(ecnr_load_config(cfgPath));
            captureRestartSnapshot();
            restartDirty = false;
        end
    end

    function onRestartControlChanged(~, ~)
        restartDirty = ~isequal(getRestartState(), restartSnapshot);
        if restartDirty
            updateStatus('Restart-required changes pending. Click Reinitialize before running.');
        else
            updateStatus('Restart-required controls match active snapshot.');
        end
    end

    function onHotControlChanged(~, ~)
        updateStatus('Hot-update controls changed for next run.');
    end

    function onReinitialize(~, ~)
        restartSnapshot = getRestartState();
        restartDirty = false;
        updateStatus('Restart-required configuration accepted for next run.');
    end

    function onRun(~, ~)
        try
            if restartDirty
                error('ecnr_gui_launch:ReinitializeRequired', 'Restart-required controls changed. Click Reinitialize before running.');
            end

            updateStatus('Running scenario...');
            drawnow;

            opts = struct();
            opts.param_overrides = collectOverrides();
            scenarioInput = buildScenarioInput();

            result = run_scenario(scenarioInput, opts);
            lastResult = result;
            
            % Generate reference run with all modules disabled for spectrogram comparison
            refOpts = struct();
            refOverrides = collectOverrides();
            refOverrides.beamformer.enabled = false;
            refOverrides.aec.enabled = false;
            refOverrides.nr.enabled = false;
            refOpts.param_overrides = refOverrides;
            
            resultWithout = run_scenario(scenarioInput, refOpts);
            
            renderResult(result, resultWithout);
            appendRunSummary(result);
            updateStatus(sprintf('Run complete: %d frames processed. Spectrograms computed.', result.frame_count));
        catch err
            updateStatus('Run failed.');
            uialert(fig, err.message, 'Scenario Failed');
        end
    end

    function onExportMetrics(~, ~)
        if isempty(lastResult)
            uialert(fig, 'Run a scenario before exporting metrics.', 'No Metrics');
            return;
        end

        outPath = resolveUiPath(metricsCsvEdit.Value);
        metrics_export_csv(lastResult.records, outPath);
        updateStatus(sprintf('Metrics exported to %s', outPath));
    end

    function overrides = collectOverrides()
        overrides = struct();
        overrides.sample_rate_hz = str2double(sampleRateField.Value);
        overrides.mic_count = str2double(micCountField.Value);
        overrides.frame = struct('length_samples', frameSizeField.Value, 'length_ms', 1000 * frameSizeField.Value / str2double(sampleRateField.Value));
        overrides.beamformer = struct('enabled', beamEnable.Value, 'algorithm', beamAlgo.Value, 'type', upper(beamAlgo.Value));
        overrides.aec = struct( ...
            'enabled', aecEnable.Value, ...
            'algorithm', aecAlgo.Value, ...
            'filter_length', aecFilterField.Value, ...
            'step_size', aecStepField.Value, ...
            'regularization', aecRegField.Value, ...
            'double_talk_threshold_db', dtdField.Value, ...
            'erle_window_frames', erleWindowField.Value);
        overrides.reference = struct('source_type', refSource.Value, 'delay_compensation_samples', refDelayField.Value);
        overrides.nr = struct('enabled', nrEnable.Value, 'algorithm', nrAlgo.Value, 'mode', nrAlgo.Value, 'aggressiveness_db', nrAggField.Value);
        overrides.mode = nrAlgo.Value;
    end

    function scenarioInput = buildScenarioInput()
        isScenario = strcmp(inputModeDrop.Value, 'Scenario JSON');
        if isScenario
            scenarioPath = resolveUiPath(scenarioEdit.Value);
            if ~isfile(scenarioPath)
                error('ecnr_gui_launch:MissingScenario', 'Scenario file not found: %s', scenarioPath);
            end
            scenarioInput = jsondecode(fileread(scenarioPath));
        else
            scenarioInput = struct();
            scenarioInput.name = 'gui_direct_wav';
            scenarioInput.config = normalizeToWorkspace(configEdit.Value);
            scenarioInput.mic_wav = normalizeToWorkspace(micEdit.Value);
            scenarioInput.ref_wav = normalizeToWorkspace(refEdit.Value);
        end

        scenarioInput.config = normalizeToWorkspace(configEdit.Value);
        scenarioInput.output_wav = normalizeToWorkspace(outputWavEdit.Value);
        scenarioInput.metrics_csv = normalizeToWorkspace(metricsCsvEdit.Value);
        if ~isfield(scenarioInput, 'name') || isempty(scenarioInput.name)
            scenarioInput.name = 'gui_run';
        end
    end

    function renderResult(result, resultWithout)
        if nargin < 2
            resultWithout = [];
        end
        
        m = result.metrics;
        convSec = estimateConvergenceSeconds(result.records, result.sample_rate_hz, frameSizeField.Value);
        headerLabel.Text = sprintf('Latest run: %s', result.name);

        metricsArea.Value = {
            sprintf('ERLE (inst): %.2f dB', valueOrNaN(m.erle_inst_db)),
            sprintf('ERLE (window): %.2f dB', valueOrNaN(m.erle_window_db)),
            sprintf('SNR in: %.2f dB', valueOrNaN(m.snr_in_db)),
            sprintf('SNR out: %.2f dB', valueOrNaN(m.snr_out_db)),
            sprintf('DTD active: %d', logical(m.dtd_active)),
            sprintf('Convergence time: %s', formatConvergence(convSec)),
            sprintf('Beamformer: %s (%d)', string(m.beamformer_algorithm), logical(m.beamformer_enabled)),
            sprintf('AEC: %s (%d)', string(m.aec_algorithm), logical(m.aec_enabled)),
            sprintf('NR: %s (%d)', string(m.nr_algorithm), logical(m.nr_enabled)),
            sprintf('Frame index: %d', m.frame_index)
        };

        summaryTable.Data = {
            'ERLE Inst (dB)', valueOrNaN(m.erle_inst_db);
            'ERLE Window (dB)', valueOrNaN(m.erle_window_db);
            'SNR In (dB)', valueOrNaN(m.snr_in_db);
            'SNR Out (dB)', valueOrNaN(m.snr_out_db);
            'DTD Active', logical(m.dtd_active);
            'Convergence (s)', formatConvergence(convSec)
        };

        y = result.y;
        showN = min(numel(y), 2000);
        plot(axWave, 1:showN, y(1:showN), 'LineWidth', 1.0);
        grid(axWave, 'on');

        erleSeries = [result.records.erle_window_db];
        plot(axErle, 1:numel(erleSeries), erleSeries, 'LineWidth', 1.2);
        grid(axErle, 'on');

        cla(axTrend);
        yyaxis(axTrend, 'left');
        snrSeries = [result.records.snr_out_db];
        plot(axTrend, 1:numel(snrSeries), snrSeries, 'LineWidth', 1.1);
        ylabel(axTrend, 'SNR Out (dB)');
        yyaxis(axTrend, 'right');
        dtdSeries = double([result.records.dtd_active]);
        stairs(axTrend, 1:numel(dtdSeries), dtdSeries, 'LineWidth', 1.1);
        ylabel(axTrend, 'DTD');
        grid(axTrend, 'on');
        
        % Compute and display spectrograms
        fs = result.sample_rate_hz;
        y_with = result.y;
        y_without = resultWithout.y;
        
        % Ensure same length for comparison
        minLen = min(numel(y_with), numel(y_without));
        y_with = y_with(1:minLen);
        y_without = y_without(1:minLen);
        
        % Spectrogram parameters
        fftnPoints = 512;
        hopLength = 128;
        window = hann(fftnPoints, 'periodic');
        freqMax = fs / 2;
        
        % Compute spectrograms
        [S_with, F_with, T_with] = spectrogram(y_with, window, fftnPoints - hopLength, fftnPoints, fs);
        [S_without, F_without, T_without] = spectrogram(y_without, window, fftnPoints - hopLength, fftnPoints, fs);
        
        % Convert to dB
        S_with_db = 20 * log10(abs(S_with) + 1e-10);
        S_without_db = 20 * log10(abs(S_without) + 1e-10);
        
        % Normalize to [-80, 0] dB range for display
        S_with_db = max(S_with_db, max(S_with_db(:)) - 80);
        S_without_db = max(S_without_db, max(S_without_db(:)) - 80);
        
        % Display spectrogram with algorithm
        imagesc(axSpectrogramWith, T_with, F_with, S_with_db);
        set(axSpectrogramWith, 'YDir', 'normal');
        colorbar(axSpectrogramWith);
        clim(axSpectrogramWith, [max(S_with_db(:)) - 80, max(S_with_db(:))]);
        
        % Display spectrogram without algorithm
        imagesc(axSpectrogramWithout, T_without, F_without, S_without_db);
        set(axSpectrogramWithout, 'YDir', 'normal');
        colorbar(axSpectrogramWithout);
        clim(axSpectrogramWithout, [max(S_without_db(:)) - 80, max(S_without_db(:))]);
        
        % Compute difference (algorithm effect)
        % Interpolate to same time-frequency grid if needed
        if numel(T_with) == numel(T_without) && numel(F_with) == numel(F_without)
            S_diff = S_with_db - S_without_db;
        else
            % Simple L2 normalization if dimensions mismatch
            minT = min(numel(T_with), numel(T_without));
            minF = min(numel(F_with), numel(F_without));
            S_diff = S_with_db(1:minF, 1:minT) - S_without_db(1:minF, 1:minT);
            T_diff = T_with(1:minT);
            F_diff = F_with(1:minF);
        end
        
        if exist('T_diff', 'var')
            imagesc(axSpectrogramDiff, T_diff, F_diff, S_diff);
        else
            imagesc(axSpectrogramDiff, T_with, F_with, S_diff);
        end
        set(axSpectrogramDiff, 'YDir', 'normal');
        cb = colorbar(axSpectrogramDiff);
        cb.Label.String = 'dB';
        
        % Set symmetric colormap limits for difference
        maxAbsDiff = max(abs(S_diff(:)));
        clim(axSpectrogramDiff, [-maxAbsDiff, maxAbsDiff]);
    end

    function appendRunSummary(result)
        convSec = estimateConvergenceSeconds(result.records, result.sample_rate_hz, frameSizeField.Value);
        row = {
            result.name,
            result.frame_count,
            valueOrNaN(result.metrics.erle_window_db),
            valueOrNaN(result.metrics.snr_out_db),
            formatConvergence(convSec)
        };
        runRows(end + 1, :) = row;
        runTable.Data = runRows;
    end

    function applyConfigToControls(cfg)
        sampleRateField.Value = num2str(cfg.sample_rate_hz);
        frameSizeField.Value = cfg.frame_size;
        micCountField.Value = num2str(cfg.mic_count);
        beamEnable.Value = logical(cfg.beamformer.enabled);
        beamAlgo.Value = lower(cfg.beamformer.algorithm);
        aecEnable.Value = logical(cfg.aec.enabled);
        aecAlgo.Value = lower(cfg.aec.algorithm);
        aecFilterField.Value = cfg.aec.filter_length;
        aecStepField.Value = cfg.aec.step_size;
        aecRegField.Value = cfg.aec.regularization;
        dtdField.Value = cfg.aec.double_talk_threshold_db;
        erleWindowField.Value = cfg.aec.erle_window_frames;
        refSource.Value = cfg.reference.source_type;
        refDelayField.Value = cfg.reference.delay_compensation_samples;
        nrEnable.Value = logical(cfg.nr.enabled);
        nrAlgo.Value = lower(cfg.nr.algorithm);
        nrAggField.Value = cfg.nr.aggressiveness_db;
    end

    function captureRestartSnapshot()
        restartSnapshot = getRestartState();
    end

    function snapshot = getRestartState()
        snapshot = struct();
        snapshot.sample_rate_hz = sampleRateField.Value;
        snapshot.frame_size = frameSizeField.Value;
        snapshot.mic_count = micCountField.Value;
        snapshot.aec_filter_length = aecFilterField.Value;
        snapshot.erle_window_frames = erleWindowField.Value;
        snapshot.beam_algorithm = beamAlgo.Value;
        snapshot.aec_algorithm = aecAlgo.Value;
        snapshot.nr_algorithm = nrAlgo.Value;
    end

    function updateStatus(msg)
        statusLabel.Text = ['Status: ' msg];
    end

    function out = resolveUiPath(in)
        if isstring(in)
            in = char(in);
        end
        if isempty(in)
            out = '';
        elseif isfile(in) || isfolder(in)
            out = in;
        else
            out = fullfile(workspaceRoot, in);
        end
    end

    function rel = normalizeToWorkspace(in)
        if isstring(in)
            in = char(in);
        end
        if startsWith(lower(in), lower(workspaceRoot))
            rel = strrep(erase(in, [workspaceRoot filesep]), '\', '/');
        else
            rel = strrep(in, '\', '/');
        end
    end

    function out = tf(v)
        if v
            out = 'on';
        else
            out = 'off';
        end
    end

    function convSec = estimateConvergenceSeconds(records, fs, frameSize)
        convSec = NaN;
        erle = [records.erle_window_db];
        if numel(erle) < 5
            return;
        end
        threshold = 6;
        stableFrames = 5;
        tol = 1.0;
        for n = stableFrames:numel(erle)
            window = erle(n - stableFrames + 1:n);
            if all(~isnan(window)) && all(window >= threshold) && (max(window) - min(window) <= tol)
                convSec = ((n - stableFrames + 1) * frameSize) / fs;
                return;
            end
        end
    end

    function out = formatConvergence(v)
        if isnan(v)
            out = 'not reached';
        else
            out = sprintf('%.3f', v);
        end
    end

    function out = valueOrNaN(v)
        if isempty(v)
            out = NaN;
        else
            out = v;
        end
    end
end
