function io = io_live_init(~)
%IO_LIVE_INIT Live I/O feasibility placeholder for Phase 1.

io = struct();
io.supported = false;
io.reason = ['Live device I/O is feasibility-gated in Phase 1 under the no-Audio-Toolbox ', ...
    'constraint. Use offline WAV scenarios as the required baseline.'];
end
