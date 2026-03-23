function [x, fs] = io_wav_read(pathIn, targetFs, requiredChannels)
%IO_WAV_READ Read WAV and normalize channels/sample rate for pipeline use.

if nargin < 1 || isempty(pathIn)
    error('io_wav_read:MissingPath', 'Input WAV path is required.');
end

[x, fs] = audioread(pathIn);

if nargin >= 2 && ~isempty(targetFs) && fs ~= targetFs
    x = resample(x, targetFs, fs);
    fs = targetFs;
end

if nargin >= 3 && ~isempty(requiredChannels)
    if size(x, 2) < requiredChannels
        x = repmat(x(:, 1), 1, requiredChannels);
    elseif size(x, 2) > requiredChannels
        x = x(:, 1:requiredChannels);
    end
end
end
