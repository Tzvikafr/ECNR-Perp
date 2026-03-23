function io_wav_write(pathOut, y, fs)
%IO_WAV_WRITE Write output waveform to WAV.

if nargin < 3
    error('io_wav_write:MissingArgs', 'pathOut, y, and fs are required.');
end

outDir = fileparts(pathOut);
if ~isempty(outDir) && ~isfolder(outDir)
    mkdir(outDir);
end

audiowrite(pathOut, y, fs);
end
