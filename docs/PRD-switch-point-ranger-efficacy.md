# PRD: Switch-Point Ranger Efficacy Phase

> Status: parked diagnostic/prototype infrastructure. This PRD is no longer the main roadmap. The zone-control RL MVP in `docs/PRD-zone-control-rl-mvp.md` supersedes it for future implementation planning. Keep this document as a reference for branch/replay discipline, reporting contracts, matching diagnostics, and non-claim hygiene.

## Problem Statement

The environment/baseline phase is complete enough to ask the next question, but not to answer it yet: does a ranger-chosen intervention produce better counterfactual outcomes than a density-matched control intervention at the same switch point?

The project has protocol, reward, Puffer binding, render, and baseline artifacts. It does not yet have honest ranger efficacy evidence. The next phase must build a staged, paired evidence path from the approved switch-point protocol to a believable read-out, without claiming final criticality, policy quality, or publication-grade SOC proof.

The main decisions this PRD locks are:

1. A 100-pair run is only a smoke/signal check.
2. Belief in ranger efficacy requires several hundred valid paired samples across many seeds.
3. No training or ranger claim counts until a paired branch/replay runner exists.
4. The project refuses SOC-proof, final-criticality, and policy-quality claims until stronger evidence exists.

## Solution

Build a switch-point efficacy roadmap around paired counterfactuals:

- start both branches from the same pre-intervention state;
- apply either the ranger-selected cell or a density-matched control cell;
- force both branches to share the same post-intervention stochastic future;
- freeze learning/adaptation during the paired read-out;
- report paired outcome deltas, invalid-pair rate, and matching quality;
- use 100 pairs only to catch wiring mistakes or a large directional signal;
- require several hundred valid pairs across many seeds before treating results as evidence that the ranger helps.

This PRD is a planning artifact. It does not create implementation issues, build the paired runner, run training/eval, or publish claims.

## User Stories

1. As Jamie, I want branch/replay infrastructure before efficacy claims, so that treatment and control differ only by intervention cell.
2. As Jamie, I want the complete pre-intervention state saved, so that paired branches start from the same grid, RNG state, timestep, and config.
3. As Jamie, I want a replay tape or equivalent deterministic schedule, so that post-intervention lightning and regrowth are shared between treatment and control.
4. As Jamie, I want branch invariants checked, so that accidental extra differences quarantine the sample instead of polluting the result.
5. As Jamie, I want density-matched controls selected from the same timestep, so that the control is a fair local alternative rather than an unrelated cell.
6. As Jamie, I want invalid pairs reported when no match exists, so that loose matching cannot manufacture a positive result.
7. As Jamie, I want density-match quality reported, so that a result can be judged alongside the quality of its controls.
8. As Jamie, I want the policy/read-out frozen during paired evaluation, so that the contrast is the selected intervention, not later adaptive divergence.
9. As Jamie, I want a paired CSV contract, so that every pair has auditable treatment, control, outcome, matching, seed, and validity fields.
10. As Jamie, I want paired reports to emphasize deltas and uncertainty, so that unrelated aggregate means do not masquerade as evidence.
11. As Jamie, I want a 100-pair signal check, so that obvious wiring failures or a very large directional effect can be detected cheaply.
12. As Jamie, I want the 100-pair check labeled as signal-only, so that it does not become a premature belief update.
13. As Jamie, I want a several-hundred-pair belief gate, so that ranger-efficacy claims wait for enough paired evidence across many seeds.
14. As Jamie, I want seed stratification recorded, so that one lucky rollout cannot dominate the conclusion.
15. As Jamie, I want HITL/local WSL boundaries explicit, so that GPU/Puffer/training work happens on the local machine, not the VPS.
16. As Jamie, I want CPU-only doc/static tests on the VPS where useful, so that contracts can be reviewed without unsafe runtime work.
17. As Jamie, I want training iteration deferred behind the paired runner, so that training smoke is not confused with efficacy evidence.
18. As Jamie, I want full-resolution global observation and flat action preserved as V1 defaults, so that the first efficacy test remains faithful to cell-level switch-point leverage.
19. As Jamie, I want 32x32/debug or crop/local-observation changes treated as performance/debug fallbacks, so that they do not quietly redefine the experiment.
20. As Jamie, I want explicit non-claims, so that the roadmap stays honest about what has and has not been proven.

## Implementation Decisions

- Use `docs/references/switch-point-test-protocol.md` as the governing protocol for pair construction, RNG/replay, frozen-policy read-out, sample counts, and stop conditions.
- Treat `docs/PRD-real-ffm-environment.md` as the completed environment/baseline phase. Do not rewrite it for this phase unless Jamie explicitly asks.
- Build branch/replay support before any efficacy run. A valid pair must restore the same pre-intervention environment state for treatment and control.
- The only intended branch difference is the intervention cell. If branch execution consumes randomness differently, use a replay tape or equivalent deterministic schedule for lightning/regrowth.
- V1 density matching uses same-timestep local tree-density terciles computed in a fixed `7x7` window around each candidate cell.
- The control is sampled from cells in the same density tercile as the ranger cell, excluding the ranger cell itself.
- If no valid same-tercile control exists at the same timestep, mark the pair invalid. Do not silently widen the match until it fits.
- Richer matching is deferred; avoid over-matching on extra features until sample starvation and signal hiding are ruled out.
- Freeze the policy/read-out during paired comparison: no learning, online updates, or adaptive second intervention that differs between branches.
- Keep the V1 action and observation contracts: flat `grid_width * grid_height + no-op` action space and full-resolution one-hot grid observation.
- Keep reward/truncation semantics from the ranger reward contract: normalized rolling living-tree fraction reward, no criticality/style reward, no intervention cost, and episode caps as truncations.
- Make paired outputs first-class artifacts: CSV rows and reports should include pair id, seed, timestep, treatment cell, control cell, density metrics, match quality, validity reason, outcome values, paired deltas, and config/protocol identifiers.
- The 100-pair run is a signal check only. It may justify debugging, threshold adjustment, or proceeding to scale-up; it must not justify a strong ranger-efficacy claim.
- The V1 paired read-out horizon is `512` post-intervention environment steps for the 100-pair signal check. The horizon is configurable and recorded in every CSV/report; treat `512` as a provisional signal-check setting, not a scientific constant.
- The primary paired outcome is burned-area avoided over the frozen read-out window: treatment-control delta in burned cells per pair, where positive means the ranger intervention avoided burned area relative to the density-matched control.
- Living-tree fraction delta, time-to-large-fire, and cluster/fire-size statistics are supporting diagnostics, not the primary decision rule.
- The belief gate is several hundred valid pairs across many seeds, with uncertainty and invalid-pair reporting. Exact N, seed schedule, and read-out horizon remain approval-gate decisions.
- Keep HITL/local WSL boundaries: GPU/Puffer/train/eval/render/raylib work belongs on Jamie's local WSL/GTX 1070 path, one command at a time when human output is needed.
- The VPS may run CPU-only unit, static, contract, docs, and compile checks, but must not run Puffer/GPU/train/eval/render/raylib/`c_render` commands for this phase.

## Testing Decisions

- Test external contracts and invariants, not internal implementation details.
- Add contract tests for branch restore/replay invariants before trusting any paired result.
- Test that treatment and control branches share the same pre-intervention state and post-intervention stochastic schedule.
- Test that invalid matches are reported, not dropped or relaxed silently.
- Test the density-matched control selector on small known grids where valid, invalid, and tie cases are obvious.
- Test the paired CSV/reporting contract with fixture data before running real paired experiments.
- Test that the 100-pair report labels itself as signal/smoke evidence only.
- Test that scaled reports include uncertainty, seed distribution, invalid-pair rate, and density-match diagnostics.
- Use CPU-only tests on the VPS for docs/static/contracts and small deterministic fixtures.
- Use local WSL/HITL only for Puffer/GPU/train/eval/render work, driven one command at a time and recorded as evidence.

## Evidence Gates

### Gate 1: Paired runner readiness

Required before any training or efficacy claim:

- branch/restore exists;
- replay or equivalent shared stochastic schedule exists;
- density-matched control selection exists;
- invalid-pair handling exists;
- paired CSV/report contract exists;
- invariant tests pass.

Passing this gate proves experiment wiring, not ranger efficacy.

### Gate 2: 100-pair signal check

Counts only as smoke/signal evidence.

A useful signal check is cleanly directional on the pre-declared paired outcome, has low/quarantined invalid-pair rate, shows acceptable density-match quality, and does not reveal replay or reporting bugs.

V1 signal checks target `100` valid pairs with a `150` attempted-pair cap. Every invalid pair must include a reason. Runs with more than `25%` invalid pairs are diagnostic only, not efficacy signal evidence. Replay or branch-invariant invalids are hard stops: no efficacy signal may be reported from that run.

The 100-pair signal check must produce paired CSV, Markdown report, and JSON summary from one invocation. The report uses fixed verdicts: `pass_signal`, `mixed_signal`, `diagnostic_only`, or `invalid_runner`. `pass_signal` requires valid runner invariants, invalid rate `<=25%`, acceptable density-match diagnostics, and directional improvement on burned-area avoided. Reports must include valid pairs, attempted pairs, invalid rate, mean/median burned-area avoided, percent of pairs where ranger avoided more burned area, uncertainty interval, density-match diagnostics, replay/invariant status, seed schedule, and read-out horizon.

A failed or mixed 100-pair check should trigger diagnosis of matching, replay, read-out horizon, outcome definition, and training quality before scale-up. If results are sensitive to the provisional `512`-step horizon, do not scale up until horizon sensitivity is understood.

### Gate 3: Several-hundred-pair belief gate

Counts as the first plausible ranger-efficacy evidence only if:

- several hundred valid pairs are collected;
- samples are spread across many seeds/episodes;
- the primary paired outcome is pre-declared as burned-area avoided over the frozen read-out window;
- uncertainty is reported;
- invalid-pair and matching diagnostics are visible;
- the result remains directionally credible after stratifying by seed or relevant baseline conditions.

The first belief gate requires `500` valid pairs across at least `50` independent seeds, with no more than `10` valid pairs per seed and no seed contributing more than `5%` of valid pairs. Attempt cap is `750` pairs. Results must report aggregate and seed-stratified burned-area avoided, invalid rate, density-match diagnostics, and uncertainty. Passing this gate supports a provisional ranger-efficacy belief only; it does not prove final criticality, SOC control, publication-grade science, or policy quality.

Even this gate does not prove final SOC behavior, final criticality, publication-grade science, or general policy quality.

## Out of Scope

- Creating GitHub implementation issues from this PRD before Jamie approves it.
- Implementing the paired runner in this PRD slice.
- Running Puffer, GPU, train, eval, render, raylib, or `c_render` commands on the VPS.
- Editing `README.md` or `docs/PRD.md` without explicit instruction.
- Rewriting `docs/PRD-real-ffm-environment.md` without explicit instruction.
- Publication-grade SOC proof.
- Final criticality claims.
- Policy-quality claims.
- Claiming the ranger helps from training smoke, render proof, or unpaired aggregates.
- Freezing final p/f constants, primary outcome, read-out horizon, or sample schedule without explicit approval.
- Multi-agent rangers, factored actions, downsampled observations, or crop/local observation unless later evidence shows V1 is too slow or unlearnable.

## Further Notes

### Veritasium forest-fire simulation UI reference

Jamie likes the feel of Veritasium's forest-fire simulation (`https://www.veritasium.com/simulation5`) as a possible future demo/report reference. Useful adaptation ideas: dark simulation-lab aesthetic, top parameter controls, seed visibility, large grid viewport, side-by-side log/log fire-size analysis, and explicit animation toggle. Treat this as UI/report inspiration only; do not let demo polish replace the paired evidence gates.

Recommended next approval gate:

Jamie should approve or change these before `/to-issues` or implementation:

1. Primary paired outcome: burned-area avoided over the frozen read-out window.
2. Density matching: same-timestep `7x7` local tree-density terciles, ranger cell excluded, invalid if no same-tercile control exists.
3. Read-out horizon: provisional `512` post-intervention steps for the 100-pair signal check, configurable and recorded.
4. Invalid-pair handling: target `100` valid pairs with a `150` attempt cap; `>25%` invalid means diagnostic only; replay/invariant invalids are hard stops.
5. 100-pair signal-check output: one invocation produces paired CSV, Markdown report, and JSON summary with fixed verdicts.
6. Belief gate: `500` valid pairs across at least `50` seeds, `10` valid pairs per seed max, no seed over `5%`, `750` attempt cap.

After approval, the next issue tree should start with branch/replay and paired CSV contracts before any paired experiment run or training claim.
