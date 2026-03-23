function [y, nrState] = nr_trad_process(nrState, e)
%NR_TRAD_PROCESS Simplified post-filter placeholder.

atten = max(0, min(0.99, nrState.aggressiveness_db / 40));
y = (1 - atten) * e;

nrState.noise_floor = 0.99 * nrState.noise_floor + 0.01 * mean(e.^2);
end
