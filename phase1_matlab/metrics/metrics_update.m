function [m, rec] = metrics_update(m, x, e, y, dtd_active, aec)
%METRICS_UPDATE Compute basic frame metrics.

p_in = mean(x.^2) + 1e-12;
p_e = mean(e.^2) + 1e-12;
p_out = mean(y.^2) + 1e-12;

rec.erle_db = 10 * log10(p_in / p_e);
rec.erle_inst_db = rec.erle_db;
rec.erle_window_db = NaN;

if nargin >= 6 && isstruct(aec)
	if isfield(aec, 'erle_inst_db')
		rec.erle_inst_db = aec.erle_inst_db;
		rec.erle_db = aec.erle_inst_db;
	end
	if isfield(aec, 'erle_window_db')
		rec.erle_window_db = aec.erle_window_db;
	end
end

rec.snr_in_db = 10 * log10(p_in);
rec.snr_out_db = 10 * log10(p_out);
rec.dtd_active = logical(dtd_active);

m.frame_index = m.frame_index + 1;
rec.frame_index = m.frame_index;
m.last = rec;
end
