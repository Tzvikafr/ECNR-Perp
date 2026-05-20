function [y, nrState] = nr_trad_process(nrState, e)
%NR_TRAD_PROCESS  STFT Wiener noise reduction with 50% OLA and Hann window.
%
%  Processes one frame of length frame_size using two 50%-overlapping
%  analysis windows per frame call.  Per-bin Wiener gain:
%      G[k] = max(floor, 1 - lambda / (SNR_post[k] + 1))
%  where lambda is derived from aggressiveness_db.
%  OLA passthrough property: sum of two consecutive Hann windows = 1.

% --- Bypass / guard ---
if ~nrState.enabled || strcmpi(nrState.algorithm, 'off') || strcmpi(nrState.algorithm, 'bypass')
    y = e;  return;
end
if strcmpi(nrState.algorithm, 'hybrid')
    y = e;  return;   % DL hybrid: guarded placeholder passthrough
end
if ~strcmpi(nrState.algorithm, 'traditional')
    error('nr_trad_process:UnsupportedAlgorithm', ...
          'Unsupported NR algorithm: %s', nrState.algorithm);
end

% --- Unpack state ---
N         = nrState.frame_size;
hop       = nrState.hop;
Nf        = nrState.fft_size;
n_bins    = nrState.n_bins;
win       = nrState.win;
alpha     = nrState.noise_smooth_alpha;
floor_lin = 10^(nrState.spectral_floor_db / 20);
% Oversubtraction: aggressiveness_db 0 dB -> lambda=1.0, 24 dB -> lambda=2.5
lambda = 1.0 + (nrState.aggressiveness_db / 24.0) * 1.5;

e = e(:);  % ensure column vector

% --- Form two 50%-overlapping analysis segments ---
%  seg1: last hop of previous frame + first hop of current frame
%  seg2: full current frame (both hops)
seg1 = [nrState.prev_in(hop+1:end); e(1:hop)];
seg2 = e;

noise_psd = nrState.noise_psd;
ola_buf   = nrState.ola_buf;
y_out     = zeros(N, 1);

for k = 1:2
    if k == 1
        seg = seg1;
    else
        seg = seg2;
    end

    % Analysis: Hann window + zero-pad FFT
    X     = fft(win .* seg, Nf);
    X_pos = X(1:n_bins);
    P     = abs(X_pos).^2;

    % Noise PSD update: IIR, gated when frame looks noise-like
    % (instantaneous power within 10 dB of current estimate)
    if mean(P) < 10.0 * (mean(noise_psd) + 1e-12)
        noise_psd = alpha .* noise_psd + (1 - alpha) .* P;
    end

    % Per-bin Wiener gain
    snr_post = P ./ (noise_psd + 1e-12);
    G = max(floor_lin, 1.0 - lambda ./ (snr_post + 1.0));

    % Reconstruct full spectrum with conjugate symmetry for real IFFT
    G_full = [G; flipud(G(2:end-1))];
    Y      = G_full .* X;

    % Synthesis: IFFT, take first N samples
    y_seg = real(ifft(Y, Nf));
    y_seg = y_seg(1:N);

    % Overlap-add: accumulate, emit one hop, shift buffer
    ola_buf = ola_buf + y_seg;
    y_out((k-1)*hop+1 : k*hop) = ola_buf(1:hop);
    ola_buf(1:hop)     = ola_buf(hop+1:end);
    ola_buf(hop+1:end) = 0;
end

% --- Write back state ---
nrState.noise_psd   = noise_psd;
nrState.prev_in     = e;
nrState.ola_buf     = ola_buf;
nrState.noise_floor = mean(noise_psd);   % kept for metrics compatibility

y = y_out;
end
