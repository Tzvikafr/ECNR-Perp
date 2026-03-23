function [e, aec] = aec_process(aec, x, ref)
%AEC_PROCESS Frame NLMS AEC with frame-level DTD gating.

% Frame-level DTD estimate.
aec.dtd_active = dtd_compute(x, ref, aec.dtd_threshold_lin);

N = numel(x);
e = zeros(N, 1);

for n = 1:N
	% Update reference history buffer with newest sample first.
	aec.x_hist = [ref(n); aec.x_hist(1:end-1)];

	y_hat = aec.w' * aec.x_hist;
	e(n) = x(n) - y_hat;

	if ~aec.dtd_active
		norm_x = (aec.x_hist' * aec.x_hist) + aec.regularization;
		aec.w = aec.w + (aec.step_size / norm_x) * e(n) * aec.x_hist;
	end
end

p_x = mean(x.^2) + 1e-12;
p_e = mean(e.^2) + 1e-12;
aec.erle_inst_db = 10 * log10(p_x / p_e);

aec.erle_hist_idx = aec.erle_hist_idx + 1;
slot = mod(double(aec.erle_hist_idx - 1), aec.erle_window_frames) + 1;
aec.erle_hist_db(slot) = aec.erle_inst_db;

valid = ~isnan(aec.erle_hist_db);
if any(valid)
	aec.erle_window_db = mean(aec.erle_hist_db(valid));
else
	aec.erle_window_db = NaN;
end
end
