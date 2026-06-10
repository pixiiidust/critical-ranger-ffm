# Local WSL paired signal check protocol

This note governs Issue #38: the first 100-pair local WSL signal/smoke review.

Current command status: `blocked_no_real_sample_provider`

Do not ask Jamie to run a 100-pair signal command yet.

The repo has the paired runner/report seam and fixture-compatible artifact writer, but it does not yet expose a reviewed command that collects real ranger-selected switch-point samples from Jamie's local environment. fixture artifacts do not count as #38 evidence, and VPS-only tests do not count as #38 evidence.

## What must exist before the local command is issued

A safe #38 command must:

- run on local WSL/GTX 1070 only;
- be given to Jamie one command at a time;
- target `100` valid pairs with a `150` attempted-pair cap;
- use the provisional `512` step frozen read-out horizon;
- must produce paired CSV, Markdown report, and JSON summary from one invocation;
- use real paired switch-point samples, not fixture rows or deterministic-only helper samples;
- preserve replay and branch invariant status in the output;
- label output as signal/smoke only, not belief evidence.

## Review vocabulary

After Jamie pastes the local command output, classify the result using only these labels:

- `pass_signal`
- `mixed_signal`
- `diagnostic_only`
- `invalid_runner`

`>25%` invalid rate means `diagnostic_only`.

replay/invariant invalids hard-stop efficacy interpretation and map to `invalid_runner` unless the generated report already states the same verdict.

## Non-claims

A #38 result is signal/smoke only. It does not prove ranger efficacy, policy quality, final criticality, publication-grade science, or SOC control.

Do not start #39 from this issue. The 500-valid-pair belief gate requires separate explicit Jamie approval.

## Tracker hygiene when a real command exists

When a real local command exists and Jamie runs it:

1. Preserve Jamie's pasted command output in the issue or PR evidence trail.
2. Record the artifact paths reported by the command.
3. Record the fixed verdict label exactly.
4. Check Issue #38 acceptance boxes only after the pasted output satisfies them.
5. Keep parent #33 clear that #39 is later belief-gate prep and requires explicit Jamie approval.
