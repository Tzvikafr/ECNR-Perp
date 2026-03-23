function active = dtd_compute(mic, ref, threshold_lin)
%DTD_COMPUTE Frame-level double-talk estimate.

p_mic = mean(mic.^2);
p_ref = mean(ref.^2) + 1e-12;
active = (p_mic / p_ref) > threshold_lin;
end
