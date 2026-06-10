# Local WSL paired signal check protocol

This note governs Issue #38: the first 100-pair local WSL signal/smoke review.

Current command status: `real_sample_provider_ready_for_review`

The repo now includes the smallest reviewed sample-provider slice for the bridge. The reviewed provider callable is `critical_ranger_ffm.reporting.local_wsl_sample_provider:build_local_wsl_switch_point_samples`.

fixture artifacts do not count as #38 evidence, and VPS-only tests do not count as #38 evidence. The provider compiles a tiny helper against the real unmanaged C environment source (`src/critical_ranger_ffm/ffm_unmanaged.c`), advances real FFM environments, snapshots their grids, and returns `SwitchPointSample` objects for the paired runner. It does not invoke Puffer, GPU training/eval, render, raylib, or `c_render`.

The bridge entry point is `python3 -m critical_ranger_ffm.reporting.local_wsl_paired_signal_check`. It now has a concrete real-provider `MODULE:CALLABLE` to replace the old placeholder.

## Reviewed bridge command shape

```bash
PYTHONPATH=src python3 -m critical_ranger_ffm.reporting.local_wsl_paired_signal_check --sample-provider critical_ranger_ffm.reporting.local_wsl_sample_provider:build_local_wsl_switch_point_samples --provider-root . --output-dir artifacts/issue38-local-wsl-paired-signal --target-valid-pairs 100 --attempted-pair-cap 150 --readout-horizon-steps 512
```

Do not replace this provider with fixture or deterministic-only helper providers.

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

## Tracker hygiene when Jamie runs the reviewed command

1. Preserve Jamie's pasted command output in the issue or PR evidence trail.
2. Record the artifact paths reported by the command.
3. Record the fixed verdict label exactly.
4. Check Issue #38 acceptance boxes only after the pasted output satisfies them.
5. Keep parent #33 clear that #39 is later belief-gate prep and requires explicit Jamie approval.
