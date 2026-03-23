function metricsStruct = ecnr_get_metrics(state)
%ECNR_GET_METRICS Return latest metrics snapshot.

if isfield(state, 'last_metrics')
    metricsStruct = state.last_metrics;
else
    metricsStruct = struct('erle_db', NaN, 'snr_in_db', NaN, 'snr_out_db', NaN, 'dtd_active', false);
end
end
