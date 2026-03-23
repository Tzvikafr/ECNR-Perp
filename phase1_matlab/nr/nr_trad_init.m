function nrState = nr_trad_init(cfg)
%NR_TRAD_INIT Initialize Traditional NR state.

nrState.enabled = cfg.nr.enabled;
nrState.algorithm = cfg.nr.algorithm;
nrState.aggressiveness_db = cfg.nr.aggressiveness_db;
nrState.noise_floor = 1e-4;
end
