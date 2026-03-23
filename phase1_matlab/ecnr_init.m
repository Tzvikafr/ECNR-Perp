function state = ecnr_init(cfg)
%ECNR_INIT Initialize Phase 1 Traditional pipeline state.

state.cfg = cfg;
state.frame_index = uint64(0);

state.beamformer = bf_init(cfg);
state.aec = aec_init(cfg);
state.nr = nr_trad_init(cfg);
state.metrics = metrics_init(cfg);

state.runtime.mode = cfg.mode;
state.runtime.started_at = datetime('now');
end
