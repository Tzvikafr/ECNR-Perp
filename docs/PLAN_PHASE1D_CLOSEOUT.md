# Plan: Finalize Phase 1D and Close All Open Issues

## Context
Phase 1D (Python PC Real-Time Demo) is code-complete but has several blockers preventing the formal closeout gate:
- `.venv` is missing `soundfile` so offline regression cannot run
- `test_simple.py` has a `traceback.print_exc(flush=True)` bug (no such keyword → `TypeError`)
- `test_audio_levels.py` crashes printing emoji on Windows console (encoding issue)
- No `.gitignore` exists, so `__pycache__/` and generated artifacts pollute git status
- `docs/PHASE2_HANDOFF.md` has a placeholder for "measured PC timings" that needs filling

This plan fixes all blockers, verifies regression passes, captures the CPU profile, and commits a clean working tree.

---

## Step 0 — Save this plan to project docs
Copy this plan to `docs/PLAN_PHASE1D_CLOSEOUT.md` in the project directory so it lives alongside `PLAN_IMPLEMENTATION.md` and `PLAN_PC_RT_PYTHON.md`.

---

## Step 1 — Fix `test_simple.py` bug
**File:** `test_simple.py:53`

Change:
```python
traceback.print_exc(flush=True)
```
To:
```python
traceback.print_exc()
```
`traceback.print_exc()` has no `flush` parameter — the current code raises `TypeError` when the stream creation fails.

---

## Step 2 — Fix `test_audio_levels.py` encoding crash + add device args
**File:** `test_audio_levels.py`

Two issues:
1. No `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` at top → emoji `⚠️` and `✓` crash Windows console
2. Device indices `(1, 4)` are hardcoded → fails on systems where those indices differ

Fix both by:
- Adding encoding reconfigure at the top (before any print)
- Adding `--device-in` and `--device-out` CLI args with defaults of `1` and `4`
- Replacing `⚠️` with `[!]` and `✓` with `[OK]` as safe fallback (encoding errors='replace' handles it but ASCII is cleaner)

---

## Step 3 — Create `.gitignore`
**New file:** `.gitignore` at repo root

Contents:
```
# Python caches
__pycache__/
*.pyc
*.pyo

# Virtual environment
.venv/

# Generated run outputs
scenarios/results/

# IDE
.vscode/
*.swp
```

Note: `metrics_baselines/phase1_offline_current.csv` stays tracked — it records the most recent verified regression pass.

---

## Step 4 — Install dependencies (shell command)
```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```
This adds `soundfile` (already in requirements.txt) to the venv.

---

## Step 5 — Run regression and capture result
```powershell
.venv\Scripts\python.exe -m ecnr_python.regression scenarios/phase1_suite.json
```
Expected: exit 0, ERLE delta >= -2.0 dB vs MATLAB baseline, SNR-out delta >= -1.0 dB vs Python baseline.

---

## Step 6 — Run offline profiler and capture timings
```powershell
.venv\Scripts\python.exe -m ecnr_python.offline_runner scenarios/phase1_offline_wav.json --profile
```
Captures per-module mean/p99 us timings. Frame budget = 20 ms (20,000 us).

---

## Step 7 — Update `docs/PHASE2_HANDOFF.md` with measured timings
After Step 6 runs, insert a new **Section 1.1 - Measured PC Timings** table into `docs/PHASE2_HANDOFF.md`
immediately after the Frame Budget table. The table will contain actual numbers from the profiler output.

---

## Step 8 — Update `docs/TASK_STATUS.md`
Mark Phase 1D as complete:
- Change `Mostly complete` to `Complete`
- Update "Last updated" date
- Check off the "Definition of Done" items that are now satisfied

---

## Step 9 — Commit clean working tree
Stage and commit all source, docs, new files, and the .gitignore.
Exclude `__pycache__/` files (now gitignored).

---

## Verification
Gate passes when:
1. `ecnr_python.regression` exits 0 (ERLE and SNR deltas within tolerance)
2. `offline_runner --profile` shows total < 100% of 20 ms frame budget on PC
3. `git status` shows only intentional files (no `__pycache__/`, no stray artifacts)
4. All files committed cleanly
