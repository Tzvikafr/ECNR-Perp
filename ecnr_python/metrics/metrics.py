"""Metrics engine — Sprint 6.

Collects per-frame records from AEC and NR sub-modules and exports a CSV
that matches the MATLAB phase1_offline_baseline.csv column layout exactly.
"""
import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import List

import numpy as np

from ecnr_python.config.ecnr_config import EcnrConfig


@dataclass
class _Record:
    frame_index: int
    erle_db: float
    erle_inst_db: float
    erle_window_db: float
    snr_in_db: float
    snr_out_db: float
    dtd_active: bool
    beamformer_enabled: bool
    beamformer_algorithm: str
    aec_enabled: bool
    aec_algorithm: str
    nr_enabled: bool
    nr_algorithm: str


class Metrics:
    def __init__(self, config: EcnrConfig):
        self._records: List[_Record] = []

        # Config flags cached for each record row
        self._bf_enabled = config.beamformer.enabled
        self._bf_algo = config.beamformer.type.name.lower()
        self._aec_enabled = config.aec.enabled
        self._nr_enabled = config.nr.enabled

        # Latest-frame summary (public, updated each call)
        self.erle_db: float = math.nan
        self.snr_in_db: float = math.nan
        self.snr_out_db: float = math.nan

    def update(self, frame_index: int,
               erle_inst_db: float, erle_window_db: float,
               snr_in_db: float, snr_out_db: float,
               dtd_active: bool) -> None:
        r = _Record(
            frame_index=frame_index,
            erle_db=erle_inst_db,
            erle_inst_db=erle_inst_db,
            erle_window_db=erle_window_db,
            snr_in_db=snr_in_db,
            snr_out_db=snr_out_db,
            dtd_active=dtd_active,
            beamformer_enabled=self._bf_enabled,
            beamformer_algorithm=self._bf_algo,
            aec_enabled=self._aec_enabled,
            aec_algorithm="nlms",
            nr_enabled=self._nr_enabled,
            nr_algorithm="traditional",
        )
        self._records.append(r)
        if not math.isnan(erle_window_db):
            self.erle_db = erle_window_db
        self.snr_in_db = snr_in_db
        self.snr_out_db = snr_out_db

    def export_csv(self, path: str) -> None:
        """Write all records to CSV matching MATLAB baseline column order."""
        if not self._records:
            print("[metrics] No records to export.")
            return
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        cols = [
            "erle_db", "erle_inst_db", "erle_window_db",
            "snr_in_db", "snr_out_db", "dtd_active", "frame_index",
            "beamformer_enabled", "beamformer_algorithm",
            "aec_enabled", "aec_algorithm",
            "nr_enabled", "nr_algorithm",
        ]
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(cols)
            for r in self._records:
                w.writerow([
                    _f(r.erle_db), _f(r.erle_inst_db), _f(r.erle_window_db),
                    _f(r.snr_in_db), _f(r.snr_out_db),
                    int(r.dtd_active), r.frame_index,
                    int(r.beamformer_enabled), r.beamformer_algorithm,
                    int(r.aec_enabled), r.aec_algorithm,
                    int(r.nr_enabled), r.nr_algorithm,
                ])
        print(f"[metrics] {len(self._records)} frames → {path}")

    def summary(self) -> dict:
        """Mean ERLE, SNR-in/out/delta and DTD count over all valid frames."""
        erle_v = [r.erle_window_db for r in self._records if not math.isnan(r.erle_window_db)]
        si_v   = [r.snr_in_db      for r in self._records if not math.isnan(r.snr_in_db)]
        so_v   = [r.snr_out_db     for r in self._records if not math.isnan(r.snr_out_db)]
        dtd_n  = sum(1 for r in self._records if r.dtd_active)
        n      = len(self._records)

        erle_m  = float(np.mean(erle_v)) if erle_v else math.nan
        si_m    = float(np.mean(si_v))   if si_v   else math.nan
        so_m    = float(np.mean(so_v))   if so_v   else math.nan
        delta_m = (so_m - si_m) if not (math.isnan(so_m) or math.isnan(si_m)) else math.nan

        return {
            "frames":          n,
            "erle_mean_db":    erle_m,
            "snr_in_mean_db":  si_m,
            "snr_out_mean_db": so_m,
            "snr_delta_mean_db": delta_m,
            "dtd_frames":      dtd_n,
        }

    def report(self) -> str:
        s = self.summary()
        nan = math.nan

        def _d(v): return f"{v:+.1f}" if not math.isnan(v) else "nan"
        return (f"ERLE={_d(s['erle_mean_db'])} dB  "
                f"SNR {_d(s['snr_in_mean_db'])}→{_d(s['snr_out_mean_db'])} dB  "
                f"SNRδ={_d(s['snr_delta_mean_db'])} dB  "
                f"DTD={s['dtd_frames']}/{s['frames']}")


def _f(v: float) -> str:
    # Use str(float()) to avoid numpy repr like "np.float64(1.23)"
    return "NaN" if math.isnan(v) else str(float(v))
