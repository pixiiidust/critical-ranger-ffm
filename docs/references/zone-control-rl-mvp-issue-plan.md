# Zone-Control RL MVP Issue Plan

Source PRD: `docs/PRD-zone-control-rl-mvp.md`

This plan is the `/to-issues` decomposition for the pivot. It keeps the first implementation sequence thin, testable, and safe for the VPS constraints.

## Route labels

- `parent`: container/tracker only.
- `afk`: executable unattended within the issue scope and guardrails.
- `hitl`: requires Jamie/Pixoid decision or local-machine output.
- `ready-for-tinker`: permits Tinker to mutate repo files and open a PR for the issue scope.
- `parallel-safe`: safe only when the issue body says dependencies and write surfaces do not overlap.

## Slice sequence

| Order | Slice | Type | Blocked by | Notes |
| --- | --- | --- | --- | --- |
| 0 | Zone-control RL MVP pivot tracker | parent | none | Container for the pivot sequence. |
| 1 | Add zone-control environment/action contract fixtures | afk | parent only | First executable slice; no training. |
| 2 | Add zone-summary observation and budget accounting contract | afk | slice 1 | Can be split if context grows. |
| 3 | Add simple zone-baseline policy contracts | afk | slice 1 | Baselines only; no RL. |
| 4 | Add evaluation report schema and anti-cheat verdicts | afk | slices 2 and 3 | Defines belief read-out before RL. |
| 5 | Add side-by-side MVP demo/report fixture | afk | slice 4 | Fixture/demo read-out, not trained evidence. |
| 6 | Define local WSL training/eval gate for first RL-vs-baseline run | hitl | slices 1-5 | Protocol only; no command is run by default. |

## Guardrails copied into issue bodies

- No VPS Puffer/GPU/train/eval/native render/raylib/`c_render`.
- No final efficacy, SOC-control, publication-grade, public-policy, or real-wildfire claims.
- No larger local WSL run unless Jamie explicitly approves the exact command.
- Do not edit `README.md` or `docs/PRD.md` without explicit instruction.
- Keep switch-point artifacts parked as diagnostics, not deleted.
