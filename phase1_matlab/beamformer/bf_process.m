function x = bf_process(bf, mic_frame)
%BF_PROCESS Apply simple DAS beamforming.

if ~bf.enabled || strcmpi(bf.algorithm, 'off') || strcmpi(bf.algorithm, 'bypass')
    x = mic_frame(:, 1);
    return;
end

if ~strcmpi(bf.algorithm, 'das')
    error('bf_process:UnsupportedAlgorithm', 'Unsupported beamformer algorithm: %s', bf.algorithm);
end

x = mic_frame * bf.weights;
end
