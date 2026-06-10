# Local WSL 500-valid-pair belief gate protocol

Issue #49 governs the first approved runtime-gate follow-up after #40. It is separate from the fixture-only UI and from the #38 signal/smoke bridge.

Current command status: `belief_gate_command_ready_for_local_wsl_review`

## Scope

This protocol gives Jamie a dedicated local WSL command for the 500-valid-pair belief gate. It must be run one command at a time and only from the local WSL checkout, not from the VPS.

The existing #38 command remains signal/smoke-only. fixture UI is not evidence, fixture rows are not evidence, and VPS-only tests are not belief evidence.

## Reviewed local WSL command shape

```bash
PYTHONPATH=src python3 -m critical_ranger_ffm.reporting.local_wsl_belief_gate_check --sample-provider critical_ranger_ffm.reporting.local_wsl_sample_provider:build_local_wsl_switch_point_samples --provider-root . --output-dir artifacts/issue49-local-wsl-belief-gate --target-valid-pairs 500 --attempted-pair-cap 750 --min-independent-seeds 50 --max-valid-pairs-per-seed 10 --max-seed-share 0.05 --readout-horizon-steps 512
```

The command writes:

- `paired_signal.csv`
- `belief_gate_report.md`
- `belief_gate_summary.json`

## Gate thresholds

The wrapper and report classify the run against the locked thresholds:

- `500` valid pairs;
- at least `50` independent seeds;
- max `10` valid pairs per seed;
- no seed over `5%` of valid pairs;
- `750` attempted-pair cap;
- read-out horizon recorded as `512` steps unless Jamie explicitly changes it.

## Required outputs

The JSON and Markdown summaries must include:

- aggregate burned-area avoided;
- seed-stratified burned-area avoided;
- invalid-rate reporting;
- density-match diagnostics;
- uncertainty reporting;
- seed distribution and dominance checks;
- replay status;
- runner invariant status.

## Review vocabulary

After Jamie pastes the local command output, classify it using only these belief-gate labels:

- `pass_belief_gate`
- `mixed_belief_gate`
- `diagnostic_only`
- `invalid_runner`

`pass_belief_gate` supports provisional ranger-efficacy belief only. It is not final criticality, not SOC control, not publication-grade science, and not policy quality.

Threshold failures, invalid rate above the configured diagnostic threshold, or seed dominance map to `diagnostic_only`. Replay or runner invariant failures map to `invalid_runner`.

## Guardrails

- Do not run the 500-pair command on the VPS.
- Do not treat fixture UI as evidence.
- Do not treat #38 signal/smoke output as belief evidence.
- Do not edit `README.md` or `docs/PRD.md` for this issue without explicit instruction.
- Do not make final efficacy, criticality, SOC, publication-grade, or policy-quality claims.

## Tracker hygiene after Jamie runs it

1. Preserve Jamie's pasted output in #49 or the PR evidence trail.
2. Record the artifact paths reported by the command.
3. Record the fixed belief-gate verdict exactly.
4. Check #49 acceptance boxes only after the pasted output satisfies them.
5. Post a #33 parent tracker comment with the verdict, thresholds, artifact paths, and non-claims.
