# Critical Ranger FFM — Project Brief

Critical Ranger FFM is a control-of-SOC experiment, not a classic SOC study. Classic forest-fire models have no agent: the system self-organizes and the researcher measures the power law. This project adds an RL ranger and asks whether steering can bend known SOC behavior by finding high-leverage switch points.

## Big question

Can a trained reinforcement-learning ranger reveal the switch points — the few high-leverage cells and moments — that steer a forest-fire system toward its self-organized critical edge?

## Why speed matters

Speed is not the prize. If the ranger reaches the critical edge faster than the unmanaged model, that is evidence the policy found leverage: actions that push the system toward criticality instead of waiting for blind self-organization to drift there.

The baseline shows that the system can self-organize, but it does not reveal where the control levers are. The ranger is interesting if it becomes a detector for those levers.

## Current scope

Start with a single-agent forest-fire environment for PufferLib Ocean 4.0, adapted from the Squared template. Keep the first version small and learnable before scaling.

## Experiment comparison

Compare two runs:

1. Baseline forest-fire model with no agent.
2. Managed forest-fire model with an RL ranger that places a firebreak or safe burn.

The key comparison is the fire-size power-law fingerprint, how quickly that fingerprint emerges, and whether ranger-chosen interventions reveal real switch points.

## Reset and truncation

Episode reset density must be defined relative to the measured critical-density band from the unmanaged smoke test. Estimate that band from the steady-state average global tree density after warm-up, not from density at ignition or cluster close. For any “faster to the edge” claim, start below the band's lower edge by about one measured band-width, clamped to `>=0`. Starting already at or above the edge makes the claim meaningless.

Stagger environment phases on reset so vectorized environments do not begin in identical correlated states.

The environment is continuing by nature. Episode caps are truncations, not terminal success or failure. Bootstrap at truncation.

## Switch point read-out

To test whether switch points are real, apply one intervention and then freeze the policy with no further ranger actions. Compare paired rollouts:

1. Ranger intervention: apply the ranger's actual action at the cell and moment chosen by the policy.
2. Control intervention: apply the same action at a random cell matched on local fuel density at the same timestep. Do not use a pure-random cell.

Paired ranger-vs-control rollouts must share the same RNG seed and the same post-intervention lightning/regrowth sequence. The only intended difference is the intervention cell; otherwise the comparison measures fire noise, not leverage.

Local fuel density uses the agent's observation window, not a fixed-size diagnostic window. Density is `tree_count / valid_cells` inside that observation window. V1 buckets density into three terciles from the observed distribution, not fixed cutoffs.

Then measure the downstream fire-size distribution. The primary contrast is ranger intervention versus matched control intervention, repeated across many paired seeds and episodes and reported with spread/uncertainty. `100` paired samples is only a signal check; several hundred across many seeds are needed before believing the effect. Do not draw all samples from one run.

Log both location and timing. Switch points are likely moments after fuel builds, not just places.

Hold richer matching, such as density plus burning-neighbor count, for v2. Over-matching can starve the control sample on a small grid.

## Reward and success separation

The ranger trains on a rolling, discounted per-step living-tree fraction with `gamma` near 1, such as `0.99+`. Keep the per-step reward small and normalized to avoid scale blowup.

Do not reward “staying near criticality” directly; that rewards the style and can be gamed. Do not add an intervention cost in v1; it can discourage action and worsen the suppression trap.

The important training lever is episode length: an episode must be long enough that monster fires can occur inside it. If suppression wins, the episode is probably too short to expose the delayed monster-fire cost. Do not use end-of-episode-only reward in v1 because sparse end reward creates a credit-assignment failure, and episodes short enough to learn from one end reward are too short to contain the monster-fire consequence.

The SOC environment should usually truncate, not terminate. Timeout is not “solved”; bootstrap value estimates at truncation instead of treating truncation as terminal, or long-horizon credit is corrupted.

Success is judged separately through the switch point test and fire-size power-law read-out, not by reward alone. Fire-size statistics are tracked separately every step.

## Scale plan

Debug scaffold defaults:

- Grid: `32x32`
- Observation window: `7x7`
- Purpose: get the PufferLib/Ocean environment training cleanly, not produce trustworthy power-law evidence

Measurement runs:

- Grid: at least `128x128`
- Purpose: trustworthy fire-size power-law fits; small grids produce noisy fingerprints
- Puffer speed matters for this scale-up, not for the first debug loop

Episode length is gated by a baseline smoke test on the measurement-size grid, not the debug grid. The unmanaged FFM must show a loose heavy-tailed / power-law-like fire-size distribution before training begins.

Known v1 tension: a `7x7` local observation may not expose globally determined switch points, but the leverage claim requires the agent to choose the intervention location. Do not use a randomly sampled focus point as the agent's location choice; that would make switch-point discovery partly luck.

## Ranger action and observation

The ranger must choose the intervention cell for the leverage claim to be valid. Randomly sampling a focus point and letting the ranger act only inside that patch is not acceptable for the main experiment because the agent would not be choosing where to act.

V1 uses the global chooser design: the agent chooses any grid cell. Start with a single full-resolution global one-hot grid observation, not a downsampled-global-plus-local-crop dual stream.

Rationale:

- The global chooser preserves the leverage claim because the agent chooses the location.
- Full-resolution observation avoids downsampling away the fine fuel/fire structure that switch points may depend on.
- A single observation stream is simpler for a first PufferLib/Ocean environment than dual global/local wiring.
- If full-resolution `128x128` is too heavy on GTX 1070, debug first at `32x32` full resolution, then scale.
- Add a local crop only if full-grid training is too slow.

Action space is flat: `grid_width * grid_height + no-op`. A flat action represents each cell exactly. Factored row/column actions are deferred because they assume separable row and column choices, while the leverage target is a specific `(row, col)` cell.

The intervention only removes fuel: if the selected cell is a tree, set it to empty before spread. If the selected cell is empty or burning, the action is an effective no-op. Do not let v1 extinguish burning cells unless that stronger power is explicitly added and named later; otherwise the intervention stops being a clean firebreak/safe-burn and contaminates the switch-point claim.

Observation encoding uses full-resolution one-hot cell state channels, not raw integer magnitude. `0`, `1`, and `2` are categories, not ordered values. Zero observation buffers every step before writing the one-hot channels.

## Baseline smoke-test gates

Run the unmanaged FFM smoke test on the measurement-size grid, `>=128x128`, not the `32x32` debug grid. A `32x32` grid may be physically too small to show a real power law, so it must not be used to conclude “no SOC.”

Gate 0 — baseline criticality:

- The unmanaged FFM fire-size distribution must be loose heavy-tailed / power-law-like.
- If the baseline does not show criticality, there is no control-of-SOC experiment yet.

Gate 1 — sample size:

- The unmanaged run must produce hundreds or more closed fire clusters.
- Do not accept a tiny sample as “enough fires.”

Gate 2 — size range:

- Fire sizes should span roughly `1.5–2` orders of magnitude.
- The tail must be populated; one monster fire is not enough.

Gate 3 — overlap rarity:

- Quiet-window Hoshen-Kopelman usually returns one connected component.
- Frequent multi-component quiet-windows mean `f` is too high for the intended SOC regime.

If any gate fails, tune `p`, `f`, or episode length before training the ranger.

Initial smoke-test defaults:

- `p = 0.01`
- `f = 1e-6`
- `f/p = 1e-4`
- Be ready to sweep to `f/p = 1e-5` or lower; SOC needs separation of timescales.
- Run until several hundred or more closed clusters, or until a step cap.
- Prefer capping by closed-cluster target first, with max steps as a safety cap; closed clusters are the quantity the smoke test actually needs.

Tuning rules:

- Too few fires: raise `f` or run longer.
- Tail truncated / no large fires: lower `f/p`.
- Too much overlap: lower `f`.
- Treat `p/f` as swept, not fixed.

Finite-size note: `128x128` may only show around `1.5` orders of magnitude in fire sizes. That can be a finite-size limit, not a tuning failure. Use `256x256+` later for a cleaner tail.

## Step update semantics

V1 step order:

1. zero buffers with `memset`
2. apply ranger intervention
3. regrow trees
4. lightning ignites trees
5. synchronously spread fire from a snapshot of burning cells
6. burn out snapshot-burning cells to empty in the same synchronous update
7. compute observation, reward, and done
8. log fire-size event counters

Fire spread must be snapshot-based. The environment reads which cells were burning at the start of the spread update and writes results into a new buffer. In-place single-pass spread is a bug because it can let fire cascade across the whole grid in one step.

Burn-out is part of the same synchronous update: burning cells ignite snapshot-neighbor trees and then become empty, matching the Drossel-Schwabl style update.

Fire-size tracking for v1 uses Design A: rare-lightning, batch cluster labeling. In the SOC regime, lightning is rare relative to fire duration, so fires should rarely overlap in time. When the grid goes quiet, run Hoshen-Kopelman on the burned mask and log each connected burned component as one fire size.

The temporal event window is bookkeeping only; a fire is defined by connectivity, not by when the grid goes quiet. Do not log a multi-fire quiet-window as one fire.

Do not suppress or defer lightning while a fire is active. The lightning rate, or `f/p` ratio, is the SOC control parameter; state-dependent gating would corrupt criticality. Instead, gate trust with the baseline smoke test: if fires frequently overlap in time, the driving rate is too high for the intended SOC regime. Lower `f` before trusting fire sizes.

Connectivity is orthogonal / 4-neighbor, matching the spread rule and the Hoshen-Kopelman pass. Keep spread connectivity and cluster-label connectivity consistent or measured fire sizes will not match the physics.

Overlap-robust live component tracking is Design B and is deferred to v2. Use it only if overlap is common despite a valid SOC-rate regime, or if batch burned-mask storage becomes too costly.

## Initial implementation target

- Grid cell states: `0=empty`, `1=tree`, `2=burning`
- Step dynamics: low-probability regrowth, rare lightning ignition, synchronous fire spread from a snapshot, burning cells burn out in the same synchronous update
- Observation: single full-resolution global one-hot grid observation
- Action: flat `grid_width * grid_height + no-op` intervention cell choice
- Reward: rolling, discounted per-step living-tree fraction with `gamma` near `1.0`, scaled roughly to `[-1, 1]`
- Buffers: zero observation, reward, and terminal/truncation buffers each step with `memset`
- Demo acceptance: synchronous spread, no in-place cascade, burn-out, HK on known masks, smoke gates, overlap reporting, whole-fire cluster logging, config loading, buffer zeroing, deterministic same-seed replay
- Config surface: grid size, observation shape, `p`, `f`, episode step cap, seed, init density policy, gamma, smoke-test cluster target, smoke-test max steps, and one connectivity value shared by spread and HK labeling
- Artifacts: Ocean `.h` logic, standalone `.c` demo, `.ini` config
- Debug mode: GTX 1070 target, `32x32` grid, build with `--float` and `--local`; avoid bf16
