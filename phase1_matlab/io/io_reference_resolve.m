function ref = io_reference_resolve(cfg, refSignal, micSignal)
%IO_REFERENCE_RESOLVE Resolve far-end reference source for offline processing.

sourceType = lower(string(cfg.reference.source_type));

switch sourceType
    case "file"
        if isempty(refSignal)
            error('io_reference_resolve:MissingReference', 'reference.source_type=file requires reference signal.');
        end
        ref = refSignal;
    case "capture_channel"
        ref = micSignal(:, 1);
    case "loopback"
        if isempty(refSignal)
            error('io_reference_resolve:MissingLoopback', 'reference.source_type=loopback requires reference signal.');
        end
        ref = refSignal;
    otherwise
        error('io_reference_resolve:UnsupportedSource', 'Unsupported reference.source_type: %s', sourceType);
end

if cfg.reference.delay_compensation_samples > 0
    d = cfg.reference.delay_compensation_samples;
    ref = [zeros(d, 1); ref(1:end-d)];
elseif cfg.reference.delay_compensation_samples < 0
    d = abs(cfg.reference.delay_compensation_samples);
    ref = [ref(d+1:end); zeros(d, 1)];
end
end
