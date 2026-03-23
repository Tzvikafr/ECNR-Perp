function x = bf_process(bf, mic_frame)
%BF_PROCESS Apply simple DAS beamforming.

if ~bf.enabled
    x = mic_frame(:, 1);
    return;
end

x = mic_frame * bf.weights;
end
