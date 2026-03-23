function m = metrics_init(~)
%METRICS_INIT Initialize metrics state.

m.frame_index = uint64(0);
m.last = struct('erle_db', NaN, 'snr_in_db', NaN, 'snr_out_db', NaN, 'dtd_active', false);
end
