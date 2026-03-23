function [e, aec] = aec_process(aec, x, ref)
%AEC_PROCESS Simplified frame NLMS placeholder.

% Frame-level DTD estimate.
aec.dtd_active = dtd_compute(x, ref, aec.dtd_threshold_lin);

% Lightweight placeholder: subtract scaled reference energy.
alpha = 0.6;
e = x - alpha * ref;

% Keep this as a scaffold; real NLMS weight update is added next.
end
