# Spectrogram Visualization Feature - GUI Enhancement

## Overview
Added spectral analysis visualization to the Phase 1 MATLAB GUI, enabling users to visually compare the effect of ECNR algorithm processing.

## Implementation Details

### GUI Layout Expansion
- Extended the right metrics panel from 6 rows to 8 rows
- Added three new spectrogram axes:
  1. **Spectrogram (With Algorithm)**: Spectral analysis of output with all modules enabled
  2. **Spectrogram (Modules Off)**: Reference spectral analysis with all processing disabled
  3. **Spectrogram Difference**: Difference plot showing algorithm effect in dB

### Automatic Dual-Run Execution
The GUI now automatically performs two scenario executions on each "Run":
1. **Primary run**: Uses current control settings (all modules may be enabled/disabled as configured)
2. **Reference run**: Same scenario but with all modules forced off (beamformer, AEC, NR disabled)

This provides immediate comparative analysis without requiring manual reconfiguration.

### Spectrogram Computation Parameters
- **FFT Size**: 512 points
- **Window**: Hann window (periodic)
- **Hop Length**: 128 samples (75% overlap)
- **Dynamic Range**: 80 dB below peak
- **Frequency Axis**: 0 to Nyquist (fs/2)
- **Time Axis**: In seconds

### Algorithm Effect Visualization
The difference spectrogram (row 8) displays:
- **Positive values (warm colors)**: Frequency bins where algorithm increased attenuation
- **Negative values (cool colors)**: Frequency bins where algorithm allowed more signal through
- **Magnitude**: Indicates strength of the algorithm effect in dB

## Code Changes

### File: `phase1_matlab/gui/ecnr_gui_launch.m`

#### 1. Extended Grid Layout (Lines 200-205)
```matlab
rightGrid = uigridlayout(rightPanel, [8 2]);  % Changed from [6 2]
rightGrid.RowHeight = {34, 120, 140, '1x', '1x', '1x', '1x', '1x'};  % Added 2 new flexible rows
```

#### 2. New Axes Definitions (Lines 235-250)
```matlab
axSpectrogramWith = uiaxes(rightGrid);      % Row 7, Column 1
axSpectrogramWithout = uiaxes(rightGrid);   % Row 7, Column 2
axSpectrogramDiff = uiaxes(rightGrid);      % Row 8, Columns 1-2
```

#### 3. Modified onRun Callback (Lines 360-420)
- Generates `refOpts` with all modules disabled
- Executes `run_scenario(scenarioInput, refOpts)` to get reference signal
- Passes both results to updated `renderResult()` function

#### 4. Enhanced renderResult Function (Lines 475-595)
- Now accepts optional second parameter: `resultWithout` (reference run result)
- Computes spectrograms using Signal Processing Toolbox `spectrogram()` function
- Displays three synchronized spectrogram images with consistent colormaps
- Handles dimension mismatches between runs gracefully

## Performance Implications
- **Runtime**: Dual execution (~2x scenario processing time)
- **Memory**: ~2x WAV signal storage for both output versions
- **Computation**: Spectrogram computation is negligible compared to ECNR processing
- **Status Display**: Updated to indicate "Spectrograms computed" upon completion

## User Workflow

### With Algorithm Enabled
1. User configures desired algorithm settings in Modules/Tuning tabs
2. Clicks "Run Scenario"
3. GUI immediately executes:
   - Run with configured settings
   - Reference run with all modules disabled
4. Three spectrograms appear showing:
   - Processed output spectrum
   - Reference (unprocessed) spectrum  
   - Visual difference map

### Interpreting Results
- **Silent/low-energy regions**: Algorithm effect is minimal
- **Speech regions**: NR typically shows strong suppression in low frequencies
- **Reference tone regions**: AEC shows strong cancellation around reference frequency
- **Broadband reduction**: Indicates overall noise/echo suppression

## Limitations & Future Enhancements
1. **Current limitation**: Always compares with all modules off
   - Future: Allow user to select reference configuration (e.g., no NR but with AEC)

2. **Fixed visualization parameters**
   - Future: Expose FFT size, window type, hop length as tunable GUI parameters

3. **Color scaling**
   - Future: Add shared colormap limits option for better cross-run comparison

4. **Frequency limits**
   - Current: Full 0-fs/2 range 
   - Future: Allow zoom to telephony band (0-4kHz) or custom range

## Testing Checklist
- [x] GUI layout extends without truncation on standard displays
- [x] Dual-run scenario execution completes without errors
- [x] Spectrograms render with proper colormaps and colorbars
- [x] Difference computation handles variable dimensions
- [x] Status updates correctly reflect spectrogram readiness
- [x] Backward compatibility maintained (renderResult works with no refResult)

## Related Files
- `phase1_matlab/gui/ecnr_gui_launch.m` — Main GUI implementation (620 lines)
- `phase1_matlab/regression/run_scenario.m` — Scenario execution engine
- `phase1_matlab/ecnr_process_frame.m` — Core frame processing pipeline

## References
- MATLAB Signal Processing Toolbox: `spectrogram()` documentation
- Time-frequency analysis best practices for audio processing
