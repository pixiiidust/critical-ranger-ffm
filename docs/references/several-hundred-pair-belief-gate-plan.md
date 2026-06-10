# Several-Hundred-Pair Belief Gate Plan

Issue #39 prepares the first several-hundred-pair belief gate after the #38 local WSL signal/smoke review. This is planning and review only. It does not run the 500-valid-pair gate.

## Sources

- Parent tracker: #33
- Prior signal/smoke issue: #38
- Governing PRD: `docs/PRD-switch-point-ranger-efficacy.md`
- Governing protocol: `docs/references/switch-point-test-protocol.md`
- #38 protocol artifact: `docs/references/local-wsl-paired-signal-check-protocol.md`

## #38 signal/smoke review before scale-up

The #38 local WSL run is reviewed first because the 100-pair output is a pipeline health and signal/smoke check, not belief evidence.

Reviewed fixed-vocabulary #38 result:

- verdict: `mixed_signal`
- `valid_pairs=100`
- `attempted_pairs=100`
- `invalid_pairs=0`
- `invalid_rate=0.000`
- `replay_status=ok`
- `runner_invariant_status=ok`
- `readout_horizon_steps=512`

Review implications before scale-up:

- Invalid rate: the run reported `invalid_rate=0.000`, so invalid-pair quarantine did not block the #38 smoke run.
- Density-match diagnostics: the belief gate must keep density-match diagnostics visible instead of treating the zero invalid rate as proof that all controls are scientifically strong.
- Replay/invariant status: `replay_status=ok` and `runner_invariant_status=ok` support runner-health confidence for the smoke path, but they do not prove efficacy.
- Uncertainty: the 100-pair result remains too small for strong belief. Uncertainty must be reported explicitly at belief-gate scale.
- Horizon sensitivity: the #38 read-out horizon was `512` steps. Treat that as the current configured horizon to record and review, not as a final scientific constant. If the result is sensitive to the horizon, stop and review before claiming belief.

## Locked belief-gate thresholds

The first belief gate keeps the PRD thresholds unchanged:

- `500 valid pairs`
- `at least 50 independent seeds`
- `max 10 valid pairs per seed`
- `no seed over 5%` of valid pairs
- `750 attempted-pair cap`

These thresholds are gate criteria for the future HITL/local run. They are not permission for the VPS to execute the gate.

## Required belief-gate outputs

The belief-gate report must include:

- aggregate burned-area avoided;
- seed-stratified burned-area avoided;
- invalid-rate reporting;
- density-match diagnostics;
- uncertainty reporting.

The primary planned outcome remains burned-area avoided over the frozen read-out window, with positive treatment-control delta meaning the ranger intervention avoided burned area relative to the density-matched control.

Seed-stratified reporting must make dominance visible. A result cannot be treated as credible belief if one lucky seed or small seed cluster carries the conclusion.

## Blocked execution state

The plan is blocked until Jamie explicitly approves scale-up after reviewing the signal artifacts and this plan.

Do not run the 500-valid-pair gate from this issue. Do not ask Jamie for a local 500-pair command from this issue unless Jamie separately approves execution.

The VPS remains CPU-safe only for this phase. It may run unit, contract, static, docs, and small deterministic checks. It must not run Puffer, GPU, train, eval, render, raylib, or `c_render` commands for this gate.

## Non-claims

Passing the future belief gate supports provisional ranger-efficacy belief only.

It is:

- not final criticality;
- not SOC control;
- not publication-grade science;
- not policy quality.

The #38 `mixed_signal` result also does not prove ranger efficacy. It only says the reviewed local signal/smoke pipeline ran with the fixed vocabulary and recorded runner-health fields.

## Approval checklist before execution

Before executing the belief gate, Jamie should explicitly approve or change:

1. The `500` valid-pair target and `750` attempted-pair cap.
2. The `50` independent-seed minimum.
3. The per-seed limits: `max 10 valid pairs per seed` and `no seed over 5%`.
4. The read-out horizon, currently recorded as `512` in #38.
5. The primary burned-area avoided decision rule and uncertainty summary.
6. The density-match diagnostics that must appear in the report.

Until that approval exists, this artifact is a reviewed plan, not an executable run instruction.
