function aec = aec_init(cfg)
%AEC_INIT Initialize simplified NLMS AEC state.

aec.enabled = cfg.aec.enabled;
aec.algorithm = cfg.aec.algorithm;
aec.filter_length = cfg.aec.filter_length;
aec.step_size = cfg.aec.step_size;
aec.regularization = cfg.aec.regularization;
aec.dtd_threshold_lin = 10^(cfg.aec.double_talk_threshold_db/10);
aec.dtd_active = false;
aec.w = zeros(aec.filter_length, 1);
aec.x_hist = zeros(aec.filter_length, 1);

% Rolling ERLE across recent frames for convergence monitoring.
if isfield(cfg.aec, 'erle_window_frames')
	aec.erle_window_frames = cfg.aec.erle_window_frames;
else
	aec.erle_window_frames = 25;
end
aec.erle_hist_db = NaN(aec.erle_window_frames, 1);
aec.erle_hist_idx = uint32(0);
aec.erle_inst_db = NaN;
aec.erle_window_db = NaN;
end
