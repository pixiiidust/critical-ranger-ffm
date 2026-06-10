# PRD: Real Unmanaged FFM Environment and Baseline Gates

> Status: retained environment/measurement spine. This PRD still governs unmanaged forest-fire physics, cluster measurement, reproducibility, and baseline smoke discipline. The agent/control roadmap has pivoted to `docs/PRD-zone-control-rl-mvp.md`.

## Problem Statement

C1 proved that Jamie's local WSL / GTX 1070 machine can build and train a PufferLib environment. That proof used a provisional shim, dummy reward, no real raylib renderer, and a small debug grid. It proved the local build/train/toolchain path, not the actual experiment or eval visuals.

The project now needs the real forest-fire environment spine: unmanaged FFM physics, whole-fire cluster measurement, reproducible logging, and baseline smoke gates. Without that, training a ranger would only optimize against guessed dynamics and fake success signals.

From Jamie's perspective, the next task is to build enough of the real environment to answer: “Does the unmanaged forest-fire model actually produce SOC-like fire-size behavior under our chosen semantics?” Only after that can the ranger be trained and tested for switch-point leverage.

## Solution

Build a real unmanaged FFM environment first, with a standalone C demo and measurable outputs. The environment should model the forest-fire dynamics and logging contract independent of policy quality.

The next slice should produce:

- deterministic unmanaged FFM stepping
- synchronous spread and burn-out semantics
- configurable grid, growth, lightning, seed, episode cap, and smoke-test limits
- whole-fire cluster sizing using 4-neighbor Hoshen-Kopelman labeling over burned masks
- CSV logs for fire clusters and smoke summaries
- baseline smoke gates that say whether the unmanaged system is ready for ranger training
- a clean path to later Puffer binding, agent reward, optional eval rendering, and switch-point tests

The key product decision: do not polish the C1 shim into “the environment.” Replace it with the real environment spine, then bind it to Puffer once unmanaged behavior is trustworthy.

## User Stories

1. As Jamie, I want the unmanaged forest-fire model to run without a ranger, so that I can prove the baseline system self-organizes before adding control.
2. As Jamie, I want each grid cell to use clear integer states, so that physics, observation, and logging all agree on what a cell means.
3. As Jamie, I want fire spread to be synchronous and snapshot-based, so that in-place cascade bugs cannot fake monster fires.
4. As Jamie, I want burning cells to burn out in the same synchronous update, so that the model matches the intended Drossel-Schwabl style dynamics.
5. As Jamie, I want orthogonal-only spread, so that cluster measurement uses the same connectivity as the physics.
6. As Jamie, I want lightning and regrowth to remain active even during fires, so that the SOC control parameter is not corrupted by state-dependent gating.
7. As Jamie, I want configurable `p`, `f`, grid size, seed, and step caps, so that I can tune the timescale separation instead of freezing constants too early.
8. As Jamie, I want the environment to log whole-fire cluster sizes, so that the criticality read-out is about fire-size statistics rather than reward.
9. As Jamie, I want fires defined by connectivity, not by the quiet-window alone, so that overlapping events are not merged into one fake fire.
10. As Jamie, I want Hoshen-Kopelman cluster labeling on burned masks, so that V1 has a simple and auditable whole-fire measurement method.
11. As Jamie, I want overlap reporting, so that I can tell when `f` is too high and fire-size statistics are untrustworthy.
12. As Jamie, I want a baseline smoke run to collect hundreds of closed clusters, so that the sample is large enough to be meaningful.
13. As Jamie, I want fire sizes to span roughly 1.5–2 orders of magnitude before training, so that the unmanaged system has a plausible heavy-tailed fingerprint.
14. As Jamie, I want the smoke test to fail loudly when the tail is empty, so that I tune dynamics before training a policy.
15. As Jamie, I want the smoke test to fail loudly when overlap is common, so that I lower `f` before trusting measurements.
16. As Jamie, I want same-seed replay to be deterministic, so that paired intervention tests can isolate the action instead of RNG noise.
17. As Jamie, I want config loading in the standalone demo, so that local WSL runs and repo tests use the same parameters.
18. As Jamie, I want CSV output with stable column contracts, so that downstream reporting and plots do not depend on ad hoc logs.
19. As Jamie, I want the debug grid to remain available at 32x32, so that Puffer/Ocean wiring can be fixed quickly on GTX 1070.
20. As Jamie, I want measurement runs to target 128x128 or larger, so that small-grid artifacts do not get mistaken for science.
21. As Jamie, I want episode caps to be truncations, not success/failure terminals, so that future value estimates are not corrupted.
22. As Jamie, I want living-tree fraction reward deferred until the environment is real, so that reward work does not distract from baseline physics.
23. As Jamie, I want the flat full-grid action contract preserved for the future ranger, so that location choice remains faithful to the leverage claim.
24. As Jamie, I want full-resolution one-hot observation preserved as the starting assumption, so that switch-point structure is not lost by downsampling.
25. As Jamie, I want local crop observation deferred unless full-grid training is too slow, so that V1 stays simple and faithful.
26. As Jamie, I want the next Puffer binding to wrap the real environment, so that train smoke proves the actual dynamics rather than a shim.
27. As Jamie, I want train-smoke, eval-load, and eval-render expectations separated, so that a successful training run is not blocked by missing draw code and a no-op render is not confused with visual proof.
28. As Jamie, I want switch-point testing deferred until the unmanaged baseline passes, so that the leverage claim rests on a real critical baseline.
29. As Jamie, I want C0.2 science kept separate from C1 wiring, so that training-method work does not muddy the baseline gates.
30. As Jamie, I want no constants frozen until measured smoke results justify them, so that early defaults do not become accidental science claims.

## Implementation Decisions

- Build the unmanaged FFM as the next requirements spine before agent reward or policy training.
- Keep the environment single-agent for V1.
- Keep state values categorical: empty, tree, burning.
- Use orthogonal / 4-neighbor connectivity for both spread and cluster labeling.
- Use this step order: clear buffers, optional intervention hook, regrow, lightning, synchronous spread, burn-out, observation/reward/truncation calculation, logging.
- Treat unmanaged mode as the first-class mode for this PRD. The intervention hook may exist but should be no-op during baseline runs.
- Preserve the future action contract: flat `grid_width * grid_height + no-op`.
- Preserve the future observation contract: full-resolution one-hot grid channels.
- Start with 32x32 for debug and build sanity, but do not use 32x32 to reject or accept SOC behavior.
- Use 128x128 or larger for baseline measurement gates.
- Expose grid size, `p`, `f`, seed, initial density policy, episode step cap, gamma placeholder, smoke cluster target, smoke max steps, and connectivity in config.
- Use rare-lightning batch cluster labeling in V1: store a burned mask while active fire exists; when the grid goes quiet, run one HK pass and log connected burned components.
- Track overlap explicitly. If quiet-window HK commonly returns multiple connected components, treat the run as a warning/failure for the intended SOC regime.
- Do not suppress lightning while fires are active. If overlap is too common, tune `f` down rather than changing the physics.
- Keep live overlap-robust component tracking out of V1 unless batch labeling is proven inadequate.
- Keep real renderer out of the unmanaged baseline gate. Text/CSV proof is enough for baseline gates.
- Treat Puffer train smoke as a build/buffer/wiring proof that does not require raylib draw code.
- Treat Puffer eval without render as a checkpoint-load/no-immediate-crash smoke when bounded by `timeout`; do not claim it proves visual rendering.
- Add a real raylib `c_render`/draw path as a separate optional debugging/eval slice after the real Puffer binding exists, unless debugging needs it earlier.
- Keep final Puffer train binding out of the first implementation pass. Add it only after the unmanaged standalone demo and baseline logs pass.
- Keep reward shaping out of the unmanaged baseline pass. Reward work starts after baseline dynamics are credible.
- Keep C0.1 slope/repeatability gates out. Do not restore them as acceptance criteria.
- Keep C0.2 science sweep separate. This PRD creates the measurement-capable environment; it does not declare final science results.

## Testing Decisions

- Test external behavior through the standalone demo and committed fixtures before relying on Puffer training.
- Reuse the existing style of Python unittest wrappers that compile C snippets and assert command outputs, CSV contracts, and deterministic replay.
- Add tests for synchronous spread using small known grids where an in-place cascade would fail visibly.
- Add tests for burn-out semantics: snapshot-burning cells ignite orthogonal tree neighbors and become empty in the same update.
- Add tests for 4-neighbor HK labeling on known masks with one component, multiple components, and empty masks.
- Add tests that spread connectivity and cluster-label connectivity share the same configured value.
- Add tests for deterministic same-seed replay across grid evolution and CSV outputs.
- Add tests that config loading changes grid size, `p`, `f`, seed, step cap, and smoke caps as expected.
- Add tests that observation buffers are zeroed before writing one-hot channels.
- Add tests that reward/terminal/truncation buffers are zeroed or written every step, even before real reward is final.
- Add tests that unmanaged baseline CSV rows include required cluster fields and stable column names.
- Add tests that overlap warnings are emitted when a quiet window contains multiple connected components.
- Add tests that smoke gates fail on deliberately insufficient samples.
- Add tests that smoke gates fail on deliberately too-narrow fire-size ranges.
- Add tests that smoke gates warn/fail on high overlap.
- Add a local-only manual verification path for Jamie's WSL/GTX 1070, but keep VPS verification CPU-only.
- Treat Puffer build/train as a later integration seam, not as the first proof of environment correctness.
- Test train smoke, eval checkpoint-load smoke, and eval render smoke as three separate gates: train can pass without rendering; eval-load can pass with no-op/missing render under timeout; visual eval requires real draw code.

## Out of Scope

- Merging PR #7 without Jamie's approval.
- Editing `README.md` or the existing umbrella `docs/PRD.md` path without explicit approval.
- Running Puffer/GPU commands on the VPS.
- Final reward tuning.
- Real renderer implementation for the unmanaged baseline gate.
- Treating Puffer eval visuals as proven before a raylib draw path exists.
- Agent policy quality claims.
- Switch-point proof claims.
- Publication-grade SOC fitting.
- Freezing final arena constants.
- Multi-agent rangers.
- Factored row/column actions.
- Downsampled global observations.
- Local crop observations unless full-grid training proves too slow.
- Live overlap-robust component tracking unless V1 batch labeling fails.
- Restoring C0.1 slope/repeatability gates.

## Further Notes

C1 local smoke changed the confidence picture: the local Puffer/CUDA path works, so the main risk has moved from “can Jamie build/train locally?” to “is the environment scientifically faithful enough to train against?”

The next work should be gated like this:

1. CPU/VPS-safe authored-code tests pass.
2. Standalone unmanaged demo passes deterministic and cluster tests.
3. Local WSL debug build passes at 32x32 with `--float --local`.
4. Measurement-size unmanaged baseline produces enough whole-fire clusters.
5. Baseline gates show a plausible heavy-tailed fire-size fingerprint.
6. Only then begin proper Puffer binding and ranger training.
7. Add visual eval/render proof separately if needed for debugging or demonstrations; it is not required for train-smoke proof.

The provisional C1 `binding.c` shim proved that Puffer can train on Jamie's machine. It should be treated as a disposable bridge, not a design to preserve. Its no-op `c_render` means C1 is a train/build/buffer proof only; real eval visuals require a later raylib draw implementation.
