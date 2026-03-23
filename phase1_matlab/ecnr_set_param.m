function state = ecnr_set_param(state, key, value)
%ECNR_SET_PARAM Update a safe runtime parameter.

switch key
    case 'beamformer.enabled'
        state.beamformer.enabled = logical(value);
    case 'aec.enabled'
        state.aec.enabled = logical(value);
    case 'aec.step_size'
        state.aec.step_size = value;
    case 'aec.regularization'
        state.aec.regularization = value;
    case 'aec.double_talk_threshold_db'
        state.aec.dtd_threshold_lin = 10^(value/10);
    case 'reference.delay_compensation_samples'
        state.cfg.reference.delay_compensation_samples = value;
    case 'nr.enabled'
        state.nr.enabled = logical(value);
    case 'nr.aggressiveness_db'
        state.nr.aggressiveness_db = value;
    otherwise
        error('ecnr_set_param:UnsupportedKey', 'Unsupported or restart-required key: %s', key);
end
end
