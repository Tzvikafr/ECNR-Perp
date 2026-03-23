function bf = bf_init(cfg)
%BF_INIT Initialize Delay-and-Sum beamformer state.

bf.enabled = cfg.beamformer.enabled && cfg.mic_count > 1;
bf.algorithm = cfg.beamformer.algorithm;
bf.mic_count = cfg.mic_count;
bf.weights = ones(cfg.mic_count, 1) ./ cfg.mic_count;
end
