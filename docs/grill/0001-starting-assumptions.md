# Starting Assumptions

These are provisional. Grill-with-docs starts by testing these, one decision at a time.

## Experiment assumptions

1. This is a control-of-SOC experiment, not a classic SOC study: the known self-organizing forest-fire baseline stays pure and uncontrolled, then the ranger shows how steering bends that known behavior.
2. The baseline is the same forest-fire dynamics with no ranger intervention.
3. “Faster” is evidence, not the main prize: it suggests the ranger found high-leverage switch points that push the system toward criticality.
4. “Critical edge” is measured from fire-size statistics, not from reward alone.
5. The first goal is proving whether policy-chosen interventions reveal real control levers, not producing a publication-grade SOC study.
6. For any faster-to-edge claim, reset initial density below the measured critical-density band's lower edge by about one measured band-width, clamped to `>=0`. Estimate the critical-density band from the steady-state average global tree density after unmanaged warm-up on the measurement grid, not from density at ignition or cluster close. Starting at or above critical density makes the claim meaningless.
7. Stagger vectorized environment phases on reset so identical resets do not correlate envs.
8. Switch points are validated with a switch point test: apply the ranger's real intervention at ranger-chosen cells/moments versus local-fuel-density-matched control cells at the same timestep, freeze the policy after the intervention, and compare which interventions shift the fire-size power-law fingerprint.
9. Paired ranger-vs-control rollouts must share the same RNG seed and post-intervention lightning/regrowth sequence; only the intervention cell should differ.
10. Timing must be logged alongside location because switch points are likely moments after fuel builds, not just places.
11. V1 matches controls only on local fuel density because over-matching can starve the control sample on a small grid. Density uses the agent's observation window, buckets are terciles from the observed distribution, and continuous matching is deferred. Richer matching, such as density plus burning-neighbor count, is deferred to v2 if v1 shows an effect and a confound needs to be killed.
12. Known v1 limitation: density alone may not be the switch-point mechanism because it ignores fire proximity.
13. Switch-point comparison is primarily ranger intervention versus matched control intervention, repeated across many paired seeds and episodes and reported with spread/uncertainty. `100` paired samples is only a signal check; several hundred across many seeds are needed before believing the effect. Do not draw all samples from one run.

## Environment assumptions

1. Start single-agent only. No multi-agent rangers in v1.
2. Use a `32x32` debug grid first to get PufferLib/Ocean training cleanly.
3. Use `128x128` or larger for measurement runs because small grids give noisy power-law fingerprints.
4. Puffer speed matters for measurement scale-up, not for the first debug phase.
5. Use integer grid states: `0=empty`, `1=tree`, `2=burning`.
6. Fire spreads orthogonally only, not diagonally.
7. Step order is fixed as: zero buffers, intervention, regrow, lightning, synchronous spread, burn-out, observation/reward/done, log.
8. Fire spread must be synchronous and snapshot-based: read which cells were burning at the start of the spread update and write to a new buffer.
9. Burn-out is part of the same synchronous update: snapshot-burning cells ignite orthogonal tree neighbors and then become empty, Drossel-Schwabl style.
10. In-place single-pass spread is a bug because it can let the whole grid burn in one step.
11. Episode length is gated by a baseline smoke test on the measurement-size grid, `>=128x128`, not the `32x32` debug grid.
12. Gate 0 is non-negotiable: unmanaged FFM must show a loose heavy-tailed / power-law-like fire-size distribution. No criticality in baseline means no control-of-SOC experiment yet.
13. Gate 1: unmanaged FFM must produce hundreds or more closed fire clusters.
14. Gate 2: fire sizes must span roughly `1.5–2` orders of magnitude with the tail populated. One monster fire is not enough.
15. Gate 3: overlap must be rare. Quiet-window HK should usually return one connected component; frequent multi-component quiet-windows mean `f` is too high.
16. If any smoke-test gate fails, tune `p`, `f`, or episode length before training the ranger.
17. Initial smoke-test defaults are `p=0.01`, `f=1e-6`, `f/p=1e-4`. Be ready to sweep to `f/p=1e-5` or lower because SOC needs separation of timescales.
18. Run the smoke test until several hundred or more closed clusters, or until a step cap. Prefer capping by closed-cluster target first, with max steps as a safety cap.
19. Tuning rules: too few fires means raise `f` or run longer; tail truncated / no large fires means lower `f/p`; too much overlap means lower `f`; treat `p/f` as swept, not fixed.
20. Finite-size note: `128x128` may only show around `1.5` orders of magnitude in fire sizes. That can be a finite-size limit, not a tuning failure. Use `256x256+` later for a cleaner tail.
21. Power-law measurement logs whole-fire cluster size, meaning total cells in each connected burned component after the quiet-window ends, not per-step burn counts and not the whole quiet-window as one fire.
22. V1 cluster sizing uses Design A: rare-lightning batch labeling. Store a burned mask while the grid is active, then when the grid goes quiet run one Hoshen-Kopelman connected-component pass.
23. A fire is defined by connectivity, not by the temporal quiet-window. The quiet-window is only the moment when it is safe to batch-label the burned mask.
24. Hoshen-Kopelman is union-find specialized for grid labeling and is simpler in v1 than live merge bookkeeping during spread.
25. Do not suppress or defer lightning during active fires because the lightning rate / `f/p` ratio is the SOC control parameter and state-dependent gating would corrupt criticality.
26. Gate trust with the baseline smoke test: if fires frequently overlap in time, the driving rate is too high for the intended SOC regime; lower `f` before trusting fire sizes.
27. Connectivity for cluster labeling is orthogonal / 4-neighbor, matching the spread rule. If measurement uses different connectivity than spread, fire sizes will not match the physics.
28. Overlap-robust live component tracking is Design B and is deferred to v2 only if overlap remains common despite a valid SOC-rate regime, or if storing the burned mask is too costly.

## Agent assumptions

1. V1 uses the global chooser design: the ranger can choose any grid cell, so the leverage claim has a real location choice.
2. Observation is a single full-resolution global one-hot grid, not a downsampled-global-plus-local-crop dual stream. This avoids downsampling away fine switch-point structure and keeps first Puffer wiring simpler.
3. If full-resolution `128x128` is too heavy on GTX 1070, debug at `32x32` full resolution first, then scale. Add a local crop only if full-grid training is too slow.
4. Action space is flat: `grid_width * grid_height + no-op`. Factored row/column action is deferred because it assumes row and column choices are separable, while the target is a specific `(row, col)` cell.
5. Observation uses one-hot cell-state channels, not raw `0/1/2` scalar values.
6. Observation buffers are zeroed every step before writing one-hot channels.
7. Firebreak / safe burn means removing fuel from a tree cell: if the selected cell is a tree, it becomes empty before spread. Selecting an empty or burning cell is an effective no-op in v1; v1 does not extinguish active fires.
8. Reward is rolling, discounted per-step living-tree fraction with `gamma` near `1.0`, such as `0.99+`, scaled roughly to `[-1, 1]`.
9. Keep per-step reward small and normalized to avoid scale blowup.
10. Do not use end-of-episode-only reward in v1 because sparse end reward creates a credit-assignment failure, and any episode short enough to learn from one end reward is too short to contain a monster fire.
11. Do not add a “stay near criticality” reward term in v1 because that rewards the style directly and can be gamed.
12. Do not add an intervention cost in v1. It can worsen the suppression trap by discouraging action.
13. The real long-horizon lever is episode length: episodes must be long enough that monster fires occur inside them. If suppression wins because its delayed monster-fire cost is not felt, the episode is too short.
14. The SOC environment is continuing; episode caps are truncations, not terminal success/failure, and value estimates should bootstrap at truncation.
15. Success is judged separately from training reward through the switch point test and fire-size power-law read-out.
16. Fire-size statistics are tracked separately every step.

## Implementation assumptions

1. Use PufferLib Ocean 4.0 and begin from the Squared template.
2. Produce three first artifacts: `.h` environment logic, `.c` standalone demo, `.ini` config.
3. On GTX 1070, debug builds use `--float` and `--local`; no bf16 path until hardware supports it.
4. Use `memset` each step to zero observation, reward, and terminal/truncation buffers.
5. The standalone `.c` demo must verify synchronous spread, no in-place cascade bug, burn-out, HK cluster sizing on known masks, unmanaged smoke gates, overlap reporting, whole-fire cluster logging, config loading, buffer zeroing, and determinism: same seed produces identical fire evolution.
6. Config must expose grid size, observation shape, `p`, `f`, episode step cap, seed, init density policy, gamma, smoke-test cluster target, smoke-test max steps, and one connectivity value shared by spread and HK labeling.

## Current open question

Resolve how the switch point test will define a real switch point without overfitting to a noisy fire-size metric.

## First unresolved decision

Define the switch point test protocol for proving that ranger-chosen cells/moments are real switch points, then define the minimum measurable success condition for “reaches the critical edge faster.”
