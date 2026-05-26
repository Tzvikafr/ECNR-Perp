"""Python regression suite runner — Sprint 6 (task 6.4).

Mirrors MATLAB run_phase1_suite_from_workspace / run_regression_suite.
Runs all scenarios in a suite JSON and compares output metrics against
frozen MATLAB baseline CSVs using the tolerances defined in the suite.

Exit code 0 = all pass, 1 = one or more failures.

Usage:
  python -m ecnr_python.regression                           # default suite
  python -m ecnr_python.regression scenarios/phase1_suite.json
  python -m ecnr_python.regression --profile                 # with CPU report
"""
import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Optional

import numpy as np

# Ensure Unicode output works on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from ecnr_python.offline_runner import run_scenario_offline


def run_regression_suite(
    suite_path: str,
    repo_root: Optional[str] = None,
    enable_profile: bool = False,
) -> bool:
    """Run every scenario in the suite and verify against baseline.

    Returns True if every scenario passes.
    """
    suite_path = Path(suite_path).resolve()
    root = Path(repo_root).resolve() if repo_root else suite_path.parent.parent

    with open(suite_path) as f:
        suite = json.load(f)

    name = suite.get("name", suite_path.stem)
    _banner(f"Python Regression Suite: {name}")

    all_pass = True

    for scenario_rel in suite.get("scenarios", []):
        scenario_path = root / scenario_rel
        print(f"\n--- Scenario: {scenario_path.name} ---")

        try:
            summary = run_scenario_offline(
                str(scenario_path),
                repo_root=str(root),
                enable_profile=enable_profile,
            )
        except Exception as exc:
            print(f"[regression] FAIL — scenario raised: {exc}")
            all_pass = False
            continue

        bc = suite.get("baseline_compare")
        if bc:
            passed = _compare_dual_baseline(
                current_csv      = str(root / bc["current_csv"]),
                matlab_baseline  = str(root / bc["matlab_baseline_csv"]) if "matlab_baseline_csv" in bc else None,
                py_baseline      = str(root / bc["py_baseline_csv"])     if "py_baseline_csv"     in bc else None,
                thresholds       = bc.get("thresholds", {}),
            )
        else:
            passed = _check_absolute(summary)

        if not passed:
            all_pass = False

    result = "PASS" if all_pass else "FAIL"
    _banner(f"Suite result: {result}")
    return all_pass


# ------------------------------------------------------------------ #
# Comparison helpers                                                   #
# ------------------------------------------------------------------ #

def _compare_dual_baseline(
    current_csv: str,
    matlab_baseline: str | None,
    py_baseline: str | None,
    thresholds: dict,
) -> bool:
    """Two-baseline comparison:

    - ERLE vs MATLAB baseline  — valid cross-language (identical metric definition)
    - SNR  vs Python baseline  — self-consistency only (MATLAB/Python SNR use
                                  different noise-floor references, so cross-
                                  language SNR comparison is not meaningful)
    """
    curr = _load_csv(current_csv)
    if curr is None:
        return False

    erle_curr    = _mean_col(curr, "erle_window_db")
    snr_out_curr = _mean_col(curr, "snr_out_db")

    all_ok = True

    # ---- ERLE vs MATLAB baseline ----
    if matlab_baseline:
        base_m = _load_csv(matlab_baseline)
        if base_m is None:
            all_ok = False
        else:
            erle_base = _mean_col(base_m, "erle_window_db")
            erle_thr  = thresholds.get("erle_window_db_min_delta_vs_matlab", -2.0)
            erle_delta = erle_curr - erle_base
            erle_ok = math.isnan(erle_base) or erle_delta >= erle_thr
            print(f"[regression]  ERLE vs MATLAB : "
                  f"current={erle_curr:+.2f}  matlab={erle_base:+.2f}  "
                  f"delta={erle_delta:+.2f} dB  threshold={erle_thr:+.2f}")
            if not erle_ok:
                print(f"[regression]  ✗ ERLE delta {erle_delta:+.2f} < {erle_thr:+.2f}")
                all_ok = False

    # ---- SNR vs Python baseline ----
    if py_baseline:
        base_py = _load_csv(py_baseline)
        if base_py is None:
            all_ok = False
        else:
            snr_base = _mean_col(base_py, "snr_out_db")
            snr_thr  = thresholds.get("snr_out_db_min_delta_vs_py", -1.0)
            snr_delta = snr_out_curr - snr_base
            snr_ok = math.isnan(snr_base) or snr_delta >= snr_thr
            print(f"[regression]  SNR-out vs Py  : "
                  f"current={snr_out_curr:+.2f}  py_base={snr_base:+.2f}  "
                  f"delta={snr_delta:+.2f} dB  threshold={snr_thr:+.2f}")
            if not snr_ok:
                print(f"[regression]  ✗ SNR-out delta {snr_delta:+.2f} < {snr_thr:+.2f}")
                all_ok = False

    print(f"[regression]  → {'PASS' if all_ok else 'FAIL'}")
    return all_ok


def _check_absolute(summary: dict) -> bool:
    """Fallback when no baseline CSV is configured."""
    erle      = summary.get("erle_mean_db",    math.nan)
    snr_delta = summary.get("snr_delta_mean_db", math.nan)

    erle_ok = math.isnan(erle)      or erle      >= 20.0
    snr_ok  = math.isnan(snr_delta) or snr_delta >=  5.0

    if not erle_ok:
        print(f"[regression]  ✗ ERLE {erle:.1f} dB < 20 dB target")
    if not snr_ok:
        print(f"[regression]  ✗ SNR-delta {snr_delta:.1f} dB < 5 dB target")

    passed = erle_ok and snr_ok
    print(f"[regression]  → {'PASS' if passed else 'FAIL'}")
    return passed


# ------------------------------------------------------------------ #
# CSV utilities                                                        #
# ------------------------------------------------------------------ #

def _load_csv(path: str):
    try:
        rows = []
        with open(path) as f:
            for row in csv.DictReader(f):
                rows.append(row)
        return rows
    except FileNotFoundError:
        print(f"[regression]  Missing CSV: {path}")
        return None


def _mean_col(rows: list, col: str) -> float:
    vals = []
    for r in rows:
        try:
            v = float(r[col])
            if not math.isnan(v):
                vals.append(v)
        except (ValueError, KeyError):
            pass
    return float(np.mean(vals)) if vals else math.nan


def _banner(msg: str) -> None:
    line = "=" * max(60, len(msg) + 4)
    print(f"\n{line}\n{msg}\n{line}")


# ------------------------------------------------------------------ #
# CLI entry point                                                      #
# ------------------------------------------------------------------ #

def _main() -> None:
    parser = argparse.ArgumentParser(description="ECNR Python Regression Suite")
    parser.add_argument("suite", nargs="?",
                        default="scenarios/phase1_suite.json",
                        help="Path to suite JSON (default: scenarios/phase1_suite.json)")
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--profile", action="store_true",
                        help="Enable per-module CPU profiling for each scenario")
    args = parser.parse_args()

    ok = run_regression_suite(
        args.suite,
        repo_root=args.repo_root,
        enable_profile=args.profile,
    )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    _main()
