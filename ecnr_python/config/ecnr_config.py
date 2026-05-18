from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
import json


class BfType(IntEnum):
    DISABLED = 0
    DAS = 1


class ArrayGeo(IntEnum):
    LINEAR = 0
    CIRCULAR = 1


class NrType(IntEnum):
    SPECTRAL_SUB = 0
    WIENER = 1


class EcnrMode(IntEnum):
    TRADITIONAL = 0
    HYBRID = 1


@dataclass
class BfConfig:
    enabled: bool = True
    type: BfType = BfType.DAS
    geometry: ArrayGeo = ArrayGeo.LINEAR
    spacing_m: float = 0.05
    steering_angle_deg: float = 0.0


@dataclass
class AecConfig:
    enabled: bool = True
    filter_length: int = 512
    step_size: float = 0.1
    regularization: float = 1e-6
    double_talk_threshold_db: float = 6.0
    erle_window_frames: int = 25


@dataclass
class NrConfig:
    enabled: bool = True
    type: NrType = NrType.WIENER
    aggressiveness_db: float = 12.0
    spectral_floor_db: float = -40.0
    noise_smooth_alpha: float = 0.95


@dataclass
class DlConfig:
    model_id: str = ""
    model_path: str = ""
    operating_point: float = 0.5


@dataclass
class RefConfig:
    source_type: str = "file"
    device_id: str = ""
    channel_index: int = 0
    delay_compensation_samples: int = 0


@dataclass
class EcnrConfig:
    schema_version: str = "1.0.0"
    sampling_rate: int = 16000
    frame_size: int = 256
    mic_count: int = 1
    mode: EcnrMode = EcnrMode.TRADITIONAL
    reference: RefConfig = field(default_factory=RefConfig)
    beamformer: BfConfig = field(default_factory=BfConfig)
    aec: AecConfig = field(default_factory=AecConfig)
    nr: NrConfig = field(default_factory=NrConfig)
    dl: DlConfig = field(default_factory=DlConfig)


def _clamp(value, lo, hi, name):
    if value < lo or value > hi:
        clamped = max(lo, min(hi, value))
        print(f"[config] WARNING: {name}={value} clamped to {clamped}")
        return clamped
    return value


def load_config(config_path: str, base_dir: str = ".") -> EcnrConfig:
    path = Path(config_path)
    if not path.is_absolute():
        path = Path(base_dir) / path

    if not path.exists():
        print(f"[config] WARNING: config file not found at {path}; using defaults")
        return EcnrConfig()

    with open(path, "r") as f:
        j = json.load(f)

    cfg = EcnrConfig()
    cfg.schema_version = j.get("schema_version", cfg.schema_version)

    cfg.sampling_rate = j.get("sample_rate_hz", cfg.sampling_rate)
    if cfg.sampling_rate not in (16000, 48000):
        print(f"[config] WARNING: unsupported sampling_rate {cfg.sampling_rate}, defaulting to 16000")
        cfg.sampling_rate = 16000

    cfg.mic_count = j.get("mic_count", cfg.mic_count)
    if cfg.mic_count not in (1, 2, 4):
        print(f"[config] WARNING: unsupported mic_count {cfg.mic_count}, defaulting to 1")
        cfg.mic_count = 1

    frame = j.get("frame", {})
    cfg.frame_size = frame.get("length_samples", cfg.frame_size)

    mode_str = j.get("mode", "traditional").lower()
    cfg.mode = EcnrMode.HYBRID if mode_str == "hybrid" else EcnrMode.TRADITIONAL

    # Beamformer
    bf = j.get("beamformer", {})
    cfg.beamformer.enabled = bf.get("enabled", cfg.beamformer.enabled)
    bf_type_str = bf.get("type", bf.get("algorithm", "das")).lower()
    cfg.beamformer.type = BfType.DAS if bf_type_str == "das" else BfType.DISABLED
    cfg.beamformer.spacing_m = _clamp(
        bf.get("spacing_m", cfg.beamformer.spacing_m), 0.01, 0.20, "beamformer.spacing_m"
    )
    cfg.beamformer.steering_angle_deg = _clamp(
        bf.get("steering_angle_deg", cfg.beamformer.steering_angle_deg), -90, 90,
        "beamformer.steering_angle_deg"
    )

    # Enforce: single mic → BF disabled (AD-02)
    if cfg.mic_count == 1:
        cfg.beamformer.type = BfType.DISABLED
        cfg.beamformer.enabled = False

    # AEC
    aec = j.get("aec", {})
    cfg.aec.enabled = aec.get("enabled", cfg.aec.enabled)
    cfg.aec.filter_length = int(
        _clamp(aec.get("filter_length", cfg.aec.filter_length), 64, 1024, "aec.filter_length")
    )
    cfg.aec.step_size = _clamp(aec.get("step_size", cfg.aec.step_size), 0.001, 1.0, "aec.step_size")
    cfg.aec.regularization = aec.get("regularization", cfg.aec.regularization)
    # dtd_compute.m converts this to linear power ratio: positive dB means
    # mic must be N dB above reference to flag double-talk.
    cfg.aec.double_talk_threshold_db = _clamp(
        aec.get("double_talk_threshold_db", cfg.aec.double_talk_threshold_db),
        -20, 40, "aec.double_talk_threshold_db"
    )
    cfg.aec.erle_window_frames = aec.get("erle_window_frames", cfg.aec.erle_window_frames)

    # Reference
    ref = j.get("reference", {})
    cfg.reference.source_type = ref.get("source_type", cfg.reference.source_type)
    cfg.reference.device_id = ref.get("device_id", cfg.reference.device_id)
    cfg.reference.channel_index = ref.get("channel_index", cfg.reference.channel_index)
    cfg.reference.delay_compensation_samples = ref.get(
        "delay_compensation_samples", cfg.reference.delay_compensation_samples
    )

    # NR
    nr = j.get("nr", {})
    cfg.nr.enabled = nr.get("enabled", cfg.nr.enabled)
    nr_type_str = nr.get("type", nr.get("mode", "wiener")).lower()
    cfg.nr.type = NrType.SPECTRAL_SUB if "sub" in nr_type_str else NrType.WIENER
    cfg.nr.aggressiveness_db = _clamp(
        nr.get("aggressiveness_db", cfg.nr.aggressiveness_db), 0, 24, "nr.aggressiveness_db"
    )
    cfg.nr.spectral_floor_db = _clamp(
        nr.get("spectral_floor_db", cfg.nr.spectral_floor_db), -60, -10, "nr.spectral_floor_db"
    )
    cfg.nr.noise_smooth_alpha = _clamp(
        nr.get("noise_smooth_alpha", cfg.nr.noise_smooth_alpha), 0.85, 0.99, "nr.noise_smooth_alpha"
    )

    # DL
    dl = j.get("dl", {})
    cfg.dl.model_id = dl.get("model_id", cfg.dl.model_id)
    cfg.dl.model_path = dl.get("model_path", cfg.dl.model_path)
    cfg.dl.operating_point = _clamp(
        dl.get("operating_point", cfg.dl.operating_point), 0.0, 1.0, "dl.operating_point"
    )

    return cfg


def load_scenario_config(scenario_path: str) -> EcnrConfig:
    """Load the ecnr config referenced by a Phase 1 scenario JSON."""
    scenario_path = Path(scenario_path)
    with open(scenario_path, "r") as f:
        scenario = json.load(f)

    config_rel = scenario.get("config")
    if not config_rel:
        return EcnrConfig()

    return load_config(config_rel, base_dir=str(scenario_path.parent.parent))
