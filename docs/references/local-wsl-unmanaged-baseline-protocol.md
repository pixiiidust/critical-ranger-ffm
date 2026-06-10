# Local WSL Unmanaged Baseline Protocol

Issue #14 scope: HITL local-machine unmanaged baseline runs only. Pixoid asks Jamie for one command at a time, waits for pasted output, then decides the next command. Do not batch a long recipe into the chat.

This protocol is for Jamie's local Ubuntu WSL checkout. It uses the unmanaged C baseline smoke and Python reporting gates. It does not require the VPS to run local-machine work.

## Hard guardrails

- Do not run Puffer/GPU commands on the VPS.
- Keep this slice unmanaged and CPU-only.
- Keep rendering out of scope here; real visual evaluation waits for the render issue after its blocker clears.
- The 32x32 debug grid is not SOC evidence. It is only a fast environment check.
- Do not claim final science from this protocol. It produces baseline readiness notes and next-action status only.

## When VS Code WSL output is unreliable

Use an external PowerShell or Windows Terminal wrapper instead of the VS Code integrated terminal. The wrapper should run inside WSL with `wsl --cd` so output returns to a normal Windows console.

PowerShell wrapper shape:

```powershell
wsl --cd /home/jamie_sim/puffer-work/critical-ranger-ffm -- bash -lc 'pwd && git status --short --branch'
```

If Jamie's local checkout is somewhere else, replace only the `--cd` path. Keep the command inside WSL.

## Phase 0: local checkout sanity

Ask Jamie to run this first, then paste all output:

```powershell
wsl --cd /home/jamie_sim/puffer-work/critical-ranger-ffm -- bash -lc 'pwd && git fetch origin && git checkout main && git pull --ff-only origin main && git rev-parse HEAD && git status --short --branch'
```

Expected result:

- command exits cleanly
- branch is `main`
- checkout is up to date with `origin/main`
- working tree is clean, or Jamie explicitly reports local-only files before continuing

If this fails, status is `fix environment bug` until the local checkout problem is solved.

## Phase 1: build and self-test unmanaged baseline smoke

Ask Jamie to run this only after Phase 0 is clean:

```powershell
wsl --cd /home/jamie_sim/puffer-work/critical-ranger-ffm -- bash -lc 'cc -std=c11 -O2 -Wall -Wextra -pedantic demos/ffm_baseline_smoke.c -lm -o /tmp/ffm_baseline_smoke && /tmp/ffm_baseline_smoke --self-test'
```

Expected result:

- compile succeeds
- self-test exits cleanly

If compile or self-test fails, status is `fix environment bug` unless the pasted output clearly points to a source regression.

## Phase 2: 32x32 debug run

Run a fast debug-only unmanaged smoke. This proves the local binary can write CSV and JSON quickly, but the debug grid is not SOC evidence.

Ask Jamie to run:

```powershell
wsl --cd /home/jamie_sim/puffer-work/critical-ranger-ffm -- bash -lc 'rm -rf reports/local-wsl-issue-14-debug && /tmp/ffm_baseline_smoke --config configs/ffm_baseline_smoke.ini --grid-width 32 --grid-height 32 --min-gate-grid-size 128 --cluster-target 40 --max-steps 50000 --warmup-steps 1000 --run-id local-wsl-issue-14-debug --out reports/local-wsl-issue-14-debug/clusters.csv --summary reports/local-wsl-issue-14-debug/summary.json && PYTHONPATH=src python3 -m critical_ranger_ffm.reporting.baseline_smoke_gates --clusters reports/local-wsl-issue-14-debug/clusters.csv --summary-json reports/local-wsl-issue-14-debug/summary.json --json; true'
```

Interpretation:

- If files are written and the gate returns JSON, the local unmanaged path works.
- A `measurement_grid_gate` warning is expected because this is 32x32.
- Do not use this run as SOC evidence.
- If the gate says too few closed clusters, use that only as a debug-run note.

## Phase 3: 128x128+ measurement candidate

Only run this after the 32x32 debug run proves the local path works. This is the first candidate that can count as baseline measurement evidence.

Ask Jamie to run:

```powershell
wsl --cd /home/jamie_sim/puffer-work/critical-ranger-ffm -- bash -lc 'rm -rf reports/local-wsl-issue-14-measurement && /tmp/ffm_baseline_smoke --config configs/ffm_baseline_smoke.ini --run-id local-wsl-issue-14-measurement --out reports/local-wsl-issue-14-measurement/clusters.csv --summary reports/local-wsl-issue-14-measurement/summary.json && PYTHONPATH=src python3 -m critical_ranger_ffm.reporting.baseline_smoke_gates --clusters reports/local-wsl-issue-14-measurement/clusters.csv --summary-json reports/local-wsl-issue-14-measurement/summary.json --json; true'
```

Expected artifacts:

- `reports/local-wsl-issue-14-measurement/clusters.csv`
- `reports/local-wsl-issue-14-measurement/summary.json`
- JSON gate output from `baseline_smoke_gates`

## Status summary rules

Summarize Jamie-pasted output into exactly one baseline status:

- `pass`: 128x128+ run completed, `measurement_grid_gate` is not a debug warning, gate status is `pass`, and no environment error appeared.
- `tune p/f`: run completed but gate output recommends tuning `p` or `f` for tail range, overlap, or ignition cadence.
- `run longer`: run completed but gate output says too few closed clusters or otherwise recommends a longer run at the same settings.
- `fix environment bug`: WSL path, git checkout, compiler, Python import, missing artifact, bad config, or command execution failed.

Record:

- local command that Jamie ran
- pasted output summary, not private machine details beyond what is needed
- generated artifact paths
- status chosen from the four values above
- whether the finding came from 32x32 debug or 128x128+ measurement

## Jamie-pasted local WSL result: 2026-06-10

Jamie ran the protocol from local Ubuntu WSL at `/home/jamie_sim/puffer-work/critical-ranger-ffm` after fast-forwarding `main` to `9d6475d935f0bace0391ffdecf5a65b62e76dfc7`.

Phase 0 checkout sanity passed:

- branch: `main`
- remote alignment: `main...origin/main`
- working tree: clean

Phase 1 build and self-test passed:

- command built `/tmp/ffm_baseline_smoke`
- self-test output: `self-test: PASS`

Phase 2 32x32 debug run completed and wrote artifacts:

- `reports/local-wsl-issue-14-debug/clusters.csv`
- `reports/local-wsl-issue-14-debug/summary.json`
- gate status: `fail`
- recommendation: `Baseline smoke gates fail; run longer.`
- reason: `36` closed clusters observed, below the `50` required for baseline smoke
- interpretation: local unmanaged path works, but this debug grid is not SOC evidence

Phase 3 128x128 measurement candidate completed and wrote artifacts:

- `reports/local-wsl-issue-14-measurement/clusters.csv`
- `reports/local-wsl-issue-14-measurement/summary.json`
- measurement grid: `pass`
- clusters: `300`
- steps run: `111233`
- fire size range: `1..16384`
- orders of magnitude: `4.214`
- overlap rate: `0.0067`
- gate status: `pass`
- recommendation: `Baseline smoke gates passed; move to measurement runs.`

Baseline status for Issue #14: `pass`.

This result is enough to complete the local WSL protocol slice. It does not claim final science; it only shows that the unmanaged baseline smoke path works locally and that the first 128x128 measurement candidate passed the smoke gates.

## Closure rule

Issue #14 is complete when the protocol is documented and at least one Jamie-pasted local run has been summarized honestly. If only the debug run succeeds, say so and keep final science open. If the 128x128+ run fails gates, close this issue only as protocol complete and route parameter tuning to the next issue.
