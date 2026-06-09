# Critical Ranger FFM Context

Critical Ranger FFM is a control-of-SOC experiment. It uses reinforcement-learning interventions to ask whether a ranger can reveal control levers in a forest-fire system whose uncontrolled baseline self-organizes toward criticality.

## Language

**Critical Edge**:
A global forest-fire regime where fire sizes show a stable heavy-tailed / power-law-like fingerprint: many small fires, rare giant fires. It is judged from fire-size statistics, not from tree-count reward alone.
_Avoid_: Good score, high reward, stable forest

**Switch Point**:
A high-leverage cell and moment where an intervention measurably shifts the later fire-size distribution toward or away from the critical fingerprint.
_Avoid_: Important cell, magic cell, best action

**Leverage Detector**:
The role of the trained ranger when its policy exposes switch points that the unmanaged self-organizing baseline does not identify.
_Avoid_: Fire suppressor, optimizer, faster baseline

**Self-Organizing Baseline**:
The unmanaged forest-fire model that drifts toward the critical edge through its native regrowth, lightning, spread, and burnout dynamics.
_Avoid_: Control run, nature, no-op agent

**Intervention**:
The ranger's real action: apply a firebreak / safe-burn at one tree cell by converting that tree to empty before fire spread. Selecting an empty or burning cell is an effective no-op in v1; v1 does not extinguish active fires.
_Avoid_: Poke, special diagnostic action, stronger intervention, extinguish-burning-cell action

**Ranger Intervention**:
An intervention applied at the cell and moment chosen by the frozen ranger policy.
_Avoid_: Agent poke, chosen poke

**Control Intervention**:
The same intervention applied at a random cell matched on v1 local fuel density and timestep. It is not a pure-random cell, because pure-random choices are often empty and make the comparison too easy.
_Avoid_: Random poke, pure-random control, over-matched control

**Local Fuel Density Match**:
The v1 control-matching rule: choose a control cell at the same timestep with comparable tree density inside the agent's observation window. Density buckets are terciles from the observed distribution, not fixed cutoffs.
_Avoid_: Fixed 5x5 match, fixed density cutoffs, full state match, continuous matching, density-plus-burn-neighbor match

**Control-of-SOC Experiment**:
An experiment that adds interventions to a known self-organizing forest-fire model to study whether steering can reveal high-leverage switch points. It is not a classic SOC study where the system is only left alone and measured.
_Avoid_: Classic SOC study, pure SOC measurement

**Rolling Living-Trees Reward**:
The v1 training reward: a rolling, discounted per-step living-tree fraction with `gamma` near 1, such as `0.99+`. It is kept small and normalized, and it is separate from the switch point test and power-law success read-out.
_Avoid_: End-only reward, criticality reward, style reward, intervention-cost reward

**Suppression Trap**:
A failure mode where the ranger learns to suppress fire in the short term, preserving trees briefly while storing up a delayed catastrophic fire. If this wins, the episode length is probably too short for the delayed monster-fire cost to be felt.
_Avoid_: Successful management, safe forest

**Debug Scaffold**:
The first training target: `32x32` grid with `7x7` local observation. Its purpose is to get PufferLib/Ocean training cleanly, not to produce trustworthy power-law evidence.
_Avoid_: Measurement setup, final grid

**Measurement Run**:
A larger run, at least `128x128`, used for trustworthy fire-size power-law fits after the debug scaffold trains cleanly. Small grids are expected to produce noisy fingerprints.
_Avoid_: Debug run, toy run

**Baseline Smoke Test**:
A pre-training gate run on the measurement-size grid, at least `128x128`, to verify the unmanaged FFM already shows loose heavy-tailed / power-law-like fire-size behavior. If baseline criticality is absent, there is no control-of-SOC experiment yet.
_Avoid_: Debug-grid SOC test, training run, agent evaluation

**Smoke-Test Gates**:
The required unmanaged-FFM checks before ranger training: baseline heavy-tail / power-law-like behavior, hundreds or more closed fire clusters, fire sizes spanning roughly `1.5–2` orders of magnitude with a populated tail, and rare overlap shown by quiet-window HK usually returning one component. Initial defaults are `p=0.01`, `f=1e-6`, `f/p=1e-4`, with `f/p=1e-5` or lower available if the tail is truncated; cap by closed-cluster target first, with max steps as safety.
_Avoid_: One monster fire, tiny sample, 32x32 no-SOC conclusion, over-driven `f/p=1e-3`, step-only smoke cap

**Synchronous Fire Update**:
The fire-spread rule that reads burning cells from a snapshot and writes the next grid into a separate buffer. Snapshot-burning cells ignite orthogonal tree neighbors and burn out to empty in the same update.
_Avoid_: In-place spread, single-pass spread

**Whole-Fire Cluster Size**:
The fire-size statistic used for the power-law read-out: total cells in a connected burned component after the fire event ends. It is not the count of cells burning in one timestep.
_Avoid_: Per-step burn count, active-fire count

**Hoshen-Kopelman Cluster Labeling**:
The v1 fire-size measurement method: store the event's burned mask, then run a Hoshen-Kopelman connected-component pass when the grid goes quiet. The quiet window is bookkeeping only; each connected component is logged as its own fire size.
_Avoid_: Live union-find during spread, label propagation during spread, logging a whole quiet-window as one fire

**Rare-Lightning Batch Design**:
The v1 cluster-sizing design. It assumes the SOC regime where lightning is rare relative to fire duration, so temporal overlap is uncommon; if overlap is frequent in the smoke test, lower `f` before trusting measurements.
_Avoid_: State-dependent lightning gating, overlap-heavy measurement

**Overlap-Robust Live Tracking**:
The deferred v2 design that tracks components live during spread and closes them independently. Use only if overlap remains common despite a valid SOC-rate regime, or if storing the burned mask is too costly.
_Avoid_: V1 requirement, first-pass implementation

**Fire Event Burned Mask**:
A temporary mask of all cells burned during a quiet-window event, used for post-event cluster labeling. Storing this mask is the v1 trade-off; live union-find is deferred to v2 only if the mask is too costly.
_Avoid_: Per-step burn log, active-only fire map

**Cluster Connectivity**:
The rule that fire clusters use orthogonal / 4-neighbor connectivity, matching the fire-spread rule. Spread physics and measurement connectivity must stay consistent.
_Avoid_: Diagonal connectivity, 8-neighbor cluster labeling

**SOC Control Parameter**:
The lightning-to-regrowth relationship, commonly expressed as the `f/p` ratio. It must not be changed state-dependently by suppressing or deferring lightning during active fires.
_Avoid_: Gated lightning, deferred lightning

**Intervention Location Choice**:
The ranger must choose the intervention cell for the leverage claim to be valid. A randomly sampled focus point is not a location choice by the agent and would make switch-point discovery partly luck.
_Avoid_: Random focus point, sampled action patch, hidden location choice

**Global Chooser Design**:
The v1 design where the ranger can choose any grid cell from a flat `grid_width * grid_height + no-op` action space, using a single full-resolution global one-hot grid observation. This preserves the switch-point location claim while avoiding dual-stream global/local wiring.
_Avoid_: Random local patch chooser, downsampled-only global observation, factored row/column action for v1

**Factored Action**:
A deferred action encoding that chooses row and column separately. It is not v1 because switch points are specific `(row, col)` cells and row/column independence can distort the claim.
_Avoid_: V1 default action encoding

**One-Hot Cell Observation**:
The required observation encoding for cell states: empty, tree, and burning are categorical channels, not raw integer magnitudes. Observation buffers are zeroed every step before writing channels.
_Avoid_: Raw 0/1/2 scalar observation

**Shared-Seed Paired Rollout**:
The switch-point evaluation rule that ranger and matched-control rollouts use the same RNG seed and post-intervention lightning/regrowth sequence. The intervention cell should be the only intended difference.
_Avoid_: Independent random rollout comparison

**Truncation**:
The normal episode cap for the continuing SOC environment. It is not terminal success/failure and value estimates should bootstrap at truncation.
_Avoid_: Treating timeout as terminal

**Critical-Density Reset**:
A reset rule where initial tree density is set relative to the measured unmanaged critical-density band. Estimate that band from the steady-state average global tree density after warm-up on the measurement grid, not from density at ignition or cluster close. For faster-to-edge claims, reset below the band's lower edge by about one measured band-width, clamped to `>=0`.
_Avoid_: Reset at or above critical density, arbitrary `critical_density - 0.1` reset, ignition-density estimate, cluster-close-density estimate

**Determinism Check**:
A demo/test requirement that the same seed produces the same fire evolution. This is necessary for shared-seed paired rollouts.
_Avoid_: Unseeded demo validation

**Switch Point Test**:
A validation test that applies one intervention, freezes the policy with no further ranger actions, and measures the downstream fire-size distribution across many shared-seed paired rollouts and episodes. The primary contrast is ranger intervention versus matched control intervention, not ranger versus unmanaged alone; `100` pairs is only a signal check, and several hundred across many seeds are needed before believing the effect.
_Avoid_: Poke test, ablation, sanity check, independent-seed comparison, all samples from one run
