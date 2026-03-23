function [y, nrState] = nr_trad_process(nrState, e)
%NR_TRAD_PROCESS Simplified post-filter placeholder.

if ~nrState.enabled || strcmpi(nrState.algorithm, 'off') || strcmpi(nrState.algorithm, 'bypass')
	y = e;
	return;
end

if strcmpi(nrState.algorithm, 'hybrid')
	y = e;
	return;
end

if ~strcmpi(nrState.algorithm, 'traditional')
	error('nr_trad_process:UnsupportedAlgorithm', 'Unsupported NR algorithm: %s', nrState.algorithm);
end

atten = max(0, min(0.99, nrState.aggressiveness_db / 40));
y = (1 - atten) * e;

nrState.noise_floor = 0.99 * nrState.noise_floor + 0.01 * mean(e.^2);
end
