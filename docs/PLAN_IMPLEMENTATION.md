## Plan: ECNR Implementation Roadmap

Recommended approach: treat Phase 1 MATLAB Traditional mode as the reference product, define a stable cross-language engine contract early, and keep Hybrid plus DSP offload behind explicit stage gates. This minimizes rework, preserves portability into AM62x, and reduces the risk that GUI or DL experimentation drives the core architecture.

**Resolved decisions (update 2026-05-14):**
- Real-time PC audio strategy: **Python + `sounddevice`** (PortAudio/WASAPI backend). MATLAB live audio remains feasibility-gated (AD-05). Python is chosen over C/C++ for sprint velocity; C/C++ is the Phase 2 production target.
- A dedicated **PC RT Demo phase** (Phase 1D) is inserted between Phase 1 MATLAB and Phase 2 embedded. Sprint-by-sprint plan: see `plan-pc-rt-python.md`.
- The Python RT implementation becomes the **behavioral reference and regression oracle** for the Phase 2 C port.

**Steps**
1. Phase 0: Architecture freeze and feasibility checks. Define the canonical processing contract across MATLAB, Python, and C/C++: frame shape, channel layout, configuration schema, metrics schema, runtime parameter update behavior, and error reporting. Decide early that the same logical module graph is reused everywhere: input routing -> optional beamformer -> AEC -> Traditional or Hybrid suppressor -> metrics/logging. This blocks all later implementation if left vague.
2. Phase 0: Resolve the three highest-risk open decisions before coding beyond prototypes. The real-time audio strategy is now resolved (Python + sounddevice — see above). Remaining decisions: choose the Hybrid integration mode for Phase 1 first release (recommend offline WAV bridge first, real-time IPC second), and define whether Phase 2 MVP is Traditional-only or must include Hybrid. These should be decided before embedded work branches.
3. Phase 1A: Build the MATLAB offline reference engine first. Implement configuration loading, mic routing for 1/2/4 channels, optional DAS beamforming, NLMS-based AEC with DTD, and Traditional post-filtering. Make every stage independently callable and testable from scripts, not only from GUI code. This step is the baseline for parity in every later phase. *(Complete)*
4. Phase 1A: Add metrics and regression harness in parallel with the MATLAB engine. Implement ERLE, convergence time, segmental SNR improvement, double-talk transparency, and a placeholder/offline-only PESQ hook. Build a repeatable offline scenario runner over WAV datasets for automotive and consumer cases. This should produce CSV or JSON artifacts that become the acceptance baseline for Phase 2 and Phase 3. *(Complete)*
5. Phase 1B: Add GUI only after the offline engine is stable. Bind controls to the configuration object, support live parameter changes where state mutation is safe, and define explicit restart-required changes for parameters that invalidate state such as sample rate, frame size, or model selection if needed. Decouple plotting refresh rate from audio processing to protect against underruns. *(Complete)*
6. Phase 1C: Add Hybrid mode as a post-AEC module with a strict contract. Recommend Phase 1 release path as offline MATLAB-to-Python integration first: MATLAB exports or pipes residual frames/features, Python performs inference, and results are re-ingested for evaluation. Only add real-time IPC after the offline Hybrid path meets quality targets and control semantics are stable.
7. Phase 1 exit gate: freeze the engine contract for porting. Publish the configuration schema, frame API semantics, stage ordering, metrics outputs, and baseline regression scenarios. Phase 1D (PC RT Demo) and Phase 2 should not start until Traditional mode parity is measurable against this frozen reference.
8. Phase 1D — PC RT Demo (Python): implement and validate real-time processing on PC using Python + sounddevice. Full sprint-by-sprint plan in `plan-pc-rt-python.md`. This phase produces: (a) a certified RT demo with live visualization, (b) the Python engine as the golden reference for Phase 2 C parity testing. Exit criteria in the sprint plan document.
9. Phase 2A: Implement the portable C/C++ core for Traditional mode only first. Port beamformer, AEC, NR, config parsing, metrics, and the frame-processing API as a platform-neutral library. Keep ALSA, file I/O, and logging outside the core. Validate frame-by-frame numeric parity against the **Python RT engine** (Phase 1D) within agreed tolerances — Python replaces MATLAB as the primary C parity reference at this stage.
10. Phase 2A: Implement AM62x Linux integration in parallel with late-stage core validation. Build the ALSA user-space application around the core, including buffer management, config load, metrics emission, and underrun recovery. Use the same scenario set as Phase 1 for offline and on-target playback/capture validation.
11. Phase 2 exit gate: verify MVP latency, CPU headroom, and audio quality before attempting Hybrid on target. Confirm the Traditional path can meet the less than 40 ms end-to-end latency requirement and can process each frame within 80 percent of frame duration with logging enabled.
12. Phase 2B: If Hybrid remains in scope for AM62x MVP, add it as a replaceable suppressor backend after Traditional parity is complete. Choose the deployment path based on the Phase 1D Hybrid timing gate result: A53 inference first if p99 < 8 ms on PC, otherwise defer to Phase 3 DSP/NPU strategy. Do not let unresolved DL deployment block Traditional release.
13. Phase 3A: Profile the A53 implementation to identify actual hotspots before offload. Use measured time breakdown per frame for beamforming, AEC, NR, feature extraction, inference, copying, and synchronization. Only offload stages that materially improve latency or power after IPC overhead is included.
14. Phase 3A: Define the DSP interface as a transport of the same engine contract, not a new architecture. Specify init, process, set-parameter, and metrics messages, buffer ownership, queue depth, and timeout behavior between A53 and C7x. Preserve the external API so Linux-side integration does not change.
15. Phase 3B: Offload compute-intensive stages incrementally, starting with the most stable Traditional blocks, then add Hybrid inference only if model size and latency budgets fit. Re-run Phase 2 regression suites plus power and tail-latency measurements after each offload milestone.
16. Cross-cutting: maintain configuration/version compatibility from the start. Store a schema version in config profiles, document units and legal ranges, and ensure MATLAB, Python, and C/C++ loaders reject invalid combinations consistently.
17. Cross-cutting: define acceptance and rollback rules per phase. Every phase should have explicit go/no-go gates tied to PRD metrics, latency targets, and a known-good fallback mode. Recommended fallback policy is Traditional-only if Hybrid or DSP paths miss schedule or quality targets.

**Relevant files**
- c:/Users/tzvika/My Drive/Learn/ECNR trials/ECNR Perp/ecnr-prd_perp_2026-03-23.md — source of phased scope, success metrics, latency targets, and platform goals.
- c:/Users/tzvika/My Drive/Learn/ECNR trials/ECNR Perp/ecnr-srs_perp_2026-03-23.md — source of module decomposition, processing API, configuration schema, and integration/testing expectations.
- c:/Users/tzvika/My Drive/Learn/ECNR trials/ECNR Perp/plan-pc-rt-python.md — sprint-by-sprint plan for Phase 1D PC real-time demo in Python.

**Verification**
1. Validate that the MATLAB offline Traditional pipeline meets or exceeds PRD targets for ERLE, convergence time, and double-talk transparency on a fixed scenario set before any GUI or embedded parity claims.
2. Verify configuration round-trip behavior across MATLAB and C/C++ loaders using the same saved profiles, including invalid-config rejection tests.
3. Compare MATLAB and C/C++ Traditional outputs on identical WAV inputs using frame-level tolerances and metric deltas, then sign off on Phase 2 parity.
4. Measure real-time processing utilization for each target frame size and sample rate, proving compute time stays below 80 percent of frame duration on PC and AM62x.
5. Run live audio stress tests with plotting enabled and disabled to confirm GUI refresh does not induce underruns in Phase 1.
6. For any Hybrid candidate, compare against Traditional on PESQ and segmental SNR improvement and reject models that improve suppression at the cost of obvious near-end distortion.
7. Before Phase 3 sign-off, measure end-to-end latency including IPC overhead and confirm the offloaded path improves either latency or power over A53-only execution.

**Decisions**
- **Resolved:** PC real-time audio uses Python + sounddevice (PortAudio/WASAPI), not MATLAB. MATLAB live I/O remains feasibility-gated (AD-05). Python is chosen over C/C++ for sprint velocity; C/C++ remains the Phase 2 production target.
- **Resolved:** A Phase 1D PC RT Demo phase is inserted before Phase 2. It produces both a certified RT demo and the golden reference for Phase 2 C parity testing.
- Recommend Phase 1 Hybrid integration start as offline MATLAB plus Python, not real-time IPC, because this de-risks model experimentation and keeps the core engine isolated.
- Recommend Phase 2 MVP be scoped as Traditional-first, with Hybrid added only after the C/C++ core and ALSA integration have met parity and latency goals.
- Recommend DAS beamforming as the first supported beamformer. MVDR-like methods should remain a later extension after baseline multi-mic support is stable.
- Treat PESQ as an offline validation metric only. Do not let it become a hard dependency inside the live processing loop.
- Keep GUI features out of the critical path for algorithm correctness; the engine and regression harness should remain usable headlessly.

**Further Considerations**
1. Hybrid deployment choice: Option A is to optimize for research velocity with Python/PyTorch first, then constrain export later. Option B is to constrain model design up front to formats TI tooling can deploy. Recommendation: choose Option B if embedded delivery dates matter more than model experimentation.
2. Real-time audio on MATLAB without Audio Toolbox is a practical risk. Recommendation: run a short feasibility spike for generic device I/O and RME Fireface before committing to GUI-heavy Phase 1 scope.
3. Runtime mutability needs an explicit policy. Recommendation: allow in-place updates only for safe tuning knobs such as step size, thresholds, and aggressiveness; require controlled restart for topology-changing settings such as sample rate, frame size, mic count, and model binary.
