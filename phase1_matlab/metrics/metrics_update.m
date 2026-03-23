function [m, rec] = metrics_update(m, x, e, y, dtd_active)
%METRICS_UPDATE Compute basic frame metrics.

p_in = mean(x.^2) + 1e-12;
p_e = mean(e.^2) + 1e-12;
p_out = mean(y.^2) + 1e-12;

rec.erle_db = 10 * log10(p_in / p_e);
rec.snr_in_db = 10 * log10(p_in);
rec.snr_out_db = 10 * log10(p_out);
rec.dtd_active = logical(dtd_active);

m.frame_index = m.frame_index + 1;
rec.frame_index = m.frame_index;
m.last = rec;
end
