function nrState = nr_trad_init(cfg)
%NR_TRAD_INIT  Initialize STFT Wiener filter NR state.

nrState.enabled           = cfg.nr.enabled;
nrState.algorithm         = cfg.nr.algorithm;

if isfield(cfg.nr, 'aggressiveness_db')
    nrState.aggressiveness_db = cfg.nr.aggressiveness_db;
else
    nrState.aggressiveness_db = 8.0;
end

nrState.spectral_floor_db  = -40.0;
nrState.noise_smooth_alpha = 0.98;
if isfield(cfg.nr, 'spectral_floor_db')
    nrState.spectral_floor_db = cfg.nr.spectral_floor_db;
end
if isfield(cfg.nr, 'noise_smooth_alpha')
    nrState.noise_smooth_alpha = cfg.nr.noise_smooth_alpha;
end

N  = cfg.frame_size;
Nf = 2^nextpow2(N);    % zero-pad to next power of 2 (512 for N=320)

if mod(N, 2) ~= 0
    error('nr_trad_init:OddFrameSize', 'frame_size must be even for 50%% OLA.');
end

nrState.frame_size = N;
nrState.hop        = N / 2;          % 50% overlap hop
nrState.fft_size   = Nf;
nrState.n_bins     = Nf / 2 + 1;    % positive-frequency bins (DC + Nyquist)
nrState.win        = hann(N, 'periodic');   % column vector
nrState.prev_in    = zeros(N, 1);    % previous input frame (for seg1 formation)
nrState.ola_buf    = zeros(N, 1);    % overlap-add accumulator
nrState.noise_psd  = ones(Nf/2+1, 1) * 1e-6;  % per-bin noise PSD estimate
nrState.noise_floor = 1e-4;          % scalar kept for metrics compatibility
end
