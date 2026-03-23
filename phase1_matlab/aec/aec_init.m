function aec = aec_init(cfg)
%AEC_INIT Initialize simplified NLMS AEC state.

aec.filter_length = cfg.aec.filter_length;
aec.step_size = cfg.aec.step_size;
aec.regularization = cfg.aec.regularization;
aec.dtd_threshold_lin = 10^(cfg.aec.double_talk_threshold_db/10);
aec.dtd_active = false;
aec.w = zeros(aec.filter_length, 1);
aec.x_hist = zeros(aec.filter_length, 1);
end
