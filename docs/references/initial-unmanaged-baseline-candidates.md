# Initial Unmanaged Baseline Candidates

Issue #15 records provisional first-pass settings from the passing unmanaged 128x128 smoke result. This is an experimental-judgment artifact for the next ranger/Puffer binding slice. It does not freeze final arena constants and it is not SOC proof.

## Source result

The candidate settings are based on the Jamie-pasted local WSL measurement run documented in `docs/references/local-wsl-unmanaged-baseline-protocol.md`.

Observed unmanaged smoke output:

- grid: `128x128`
- clusters: `300`
- steps run: `111233`
- fire size range: `1..16384`
- orders of magnitude: `4.214`
- overlap rate: `0.0067`
- gate status: `pass`
- recommendation: `Baseline smoke gates passed; move to measurement runs.`

Interpretation:

- The run produced hundreds of closed clusters, enough for the first binding pass.
- The size range spans the full 128x128 grid area in this run, so the tail is populated for smoke purposes.
- The overlap rate is low, so this first pass is not obviously over-driven by overlapping fires.
- These facts justify carrying the current smoke parameters into the first ranger/Puffer binding pass as starting candidates only.

## Provisional first-pass candidate

Use these as the first-pass candidate values for the next binding slice:

- p: `0.01`
- f: `0.000001`
- f/p: `0.0001`

Reasoning:

- The baseline gates passed at these settings on a measurement-size `128x128` run.
- The run reached `300` closed clusters before the `200000` step safety cap.
- The observed overlap rate `0.0067` is far below the smoke gate warning region.
- The observed tail is not truncated in the smoke output.

Do not treat these as final constants. Treat `p`, `f`, and especially `f/p` as swept parameters after the first binding works. If later runs show a truncated tail, lower `f/p`. If later runs show too much overlap, lower `f`. If later runs show too few closed clusters, run longer first, then consider raising `f` only with the overlap risk documented.

## Minimum credible first binding settings

For the first ranger/Puffer binding pass, carry forward the smallest settings that preserve the passed unmanaged baseline shape:

- grid: `128x128`
- warmup: `10000` steps
- closed-cluster target: `300`
- smoke-gate minimum: `50` closed clusters
- max steps: `200000`
- measurement gate: use `128x128` or larger only
- run cap: cap by closed-cluster target first, with max steps as a safety cap

The first binding pass may use these settings to prove that the real unmanaged/managed environment wiring, flat action contract, observation contract, and buffers can run. It should not require final tuned science metrics before the binding exists.

## If gates fail later

The Issue #14 128x128 gate passed, so Issue #15 does not need a new tuning knob before #16 starts. If a repeat run fails later, use this order:

1. Too few closed clusters with acceptable overlap: run longer or raise the closed-cluster target cap before changing physics.
2. Tail truncated or no large fires: lower `f/p` and document the sweep.
3. Too much overlap: lower `f` and rerun before trusting fire-size statistics.
4. Environment/build failures: fix the environment path; do not reinterpret them as FFM parameter evidence.

## Scope guardrails

- This artifact does not freeze final arena constants.
- C0.2 science conclusions are out of scope.
- The passing smoke run is not SOC proof.
- Do not use this artifact as permission to run Puffer, GPU, train, eval, render, raylib, or `c_render` work on the VPS.
- Do not claim final criticality from the smoke run; it only selects a credible first unmanaged baseline candidate for binding work.
