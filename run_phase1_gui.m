% run_phase1_gui.m  —  Launch ECNR Phase 1 tuning GUI.
%
% Run from the MATLAB command window (workspace root):
%   run_phase1_gui
%
% Or from PowerShell (opens interactive MATLAB session with GUI):
%   & "C:\Program Files\MATLAB\R2023b\bin\matlab.exe" -r "run('c:/Users/tzvika/My Drive/Learn/ECNR trials/ECNR Perp/run_phase1_gui.m')"

scriptDir = fileparts(mfilename('fullpath'));
if ~isempty(scriptDir)
    cd(scriptDir);
end
addpath(genpath(fullfile(pwd, 'phase1_matlab')));
ecnr_gui_launch();
