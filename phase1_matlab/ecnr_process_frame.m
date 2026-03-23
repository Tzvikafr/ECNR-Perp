function [out_frame, state] = ecnr_process_frame(state, mic_frame, ref_frame)
%ECNR_PROCESS_FRAME Process one frame through Traditional ECNR chain.

cfg = state.cfg;
expectedMicRows = cfg.frame_size;

if size(mic_frame, 1) ~= expectedMicRows
    error('ecnr_process_frame:InvalidMicFrame', 'mic_frame rows must equal frame_size.');
end
if size(ref_frame, 1) ~= cfg.frame_size
    error('ecnr_process_frame:InvalidRefFrame', 'ref_frame rows must equal frame_size.');
end

if cfg.mic_count == 1
    x = mic_frame(:, 1);
else
    x = bf_process(state.beamformer, mic_frame);
end

[e, state.aec] = aec_process(state.aec, x, ref_frame);
[y, state.nr] = nr_trad_process(state.nr, e);

[state.metrics, rec] = metrics_update(state.metrics, x, e, y, state.aec.dtd_active);
state.last_metrics = rec;

state.frame_index = state.frame_index + 1;
out_frame = y;
end
