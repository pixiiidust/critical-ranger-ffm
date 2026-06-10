# Critical Ranger FFM — Project Brief

Critical Ranger FFM is a toy control-of-SOC experiment. It uses a forest-fire model to ask whether learned zone-level interventions can reduce catastrophic fire cascades better than simple rule baselines, without winning by clearing the forest.

## Current roadmap

The current roadmap is the **Zone-Control RL MVP**.

Main question:

> Can reinforcement learning reduce mega-fire frequency in a toy self-organized forest-fire model better than honest simple baselines, while preserving acceptable forest density and staying within an intervention budget?

The previous switch-point / single-cell efficacy roadmap is parked as diagnostic infrastructure. It produced useful branch/replay, reporting, control-selection, and non-claim discipline, but it is no longer the main science proof.

## Why the pivot happened

The single-cell switch-point gate became dominated by matching and geometry confounds. The `mixed_belief_gate` result from the #49/#51 line showed healthy plumbing but weak/negative outcome signal, with treatment samples biased toward edge/corner geometry.

The old gate was a microscope. It helped debug the project. But the project now needs the machine: zone-level control over time, compared against strong simple baselines.

## V1 product shape

V1 is a zone-control toy environment:

- forest grid with categorical cell states;
- zones as the intervention unit;
- action space: no-op or thin exactly one selected zone;
- fixed decision interval rather than action every physics tick;
- zone-summary observations;
- budget/cost accounting;
- evaluation against honest rule baselines.

Practical first target:

- `64x64` forest grid;
- `8x8` zone grid;
- `64` selectable zones plus no-op.

A `100x100` forest with `10x10` zones remains a later/demo-scale option if training and visualization cost are acceptable.

## Success read-out

Primary success metric:

> Mega-fire frequency reduction versus the strongest simple baseline, subject to acceptable average/minimum tree density and intervention-budget constraints.

Supporting metrics:

- max fire size;
- total burned area;
- fire-size distribution;
- average tree density;
- minimum tree density;
- intervention cost;
- budget utilization.

Reward is not the belief read-out. Reward is for learning; evaluation metrics decide whether the MVP worked.

## Baselines to beat

RL only matters if it beats honest simple rules under the same seeds, budget, decision interval, and report schema.

V1 baselines:

1. no action;
2. random zone thinning;
3. densest-zone thinning;
4. largest-cluster-edge zone thinning;
5. fixed firebreak/grid-pattern thinning;
6. periodic thinning.

## Reward and anti-cheat rules

Initial reward shape should include:

- burned-area penalty;
- mega-fire penalty;
- treatment-cost penalty;
- low-density-collapse penalty;
- over-clearing penalty;
- bounded healthy-density band shaping.

Anti-cheat failures:

- agent clears the forest to avoid fire;
- agent spends unlimited treatment;
- agent only delays catastrophe beyond the episode horizon;
- agent beats no-op but loses to a simple rule baseline;
- reward improves while density/cost constraints fail.

## Evidence gates

### Gate 1: Zone-control environment contract

Proves the environment and action contracts are wired, not that RL works.

Required:

- no-op and one-zone-thinning actions;
- deterministic zone indexing;
- decision interval enforcement;
- treatment cost/budget tracking;
- stable zone-summary observations;
- fixture tests.

### Gate 2: Baseline evaluation contract

Proves honest comparisons can be run, not that RL wins.

Required:

- all V1 baselines;
- same budget, seeds, decision interval, and report schema;
- reports with mega-fire, burn-area, fire-size, density, and cost metrics;
- visible failure for clearing/over-budget wins.

### Gate 3: First RL-vs-baseline MVP read-out

Counts only as toy-environment MVP evidence.

Required:

- compare RL against the strongest simple baseline;
- reduce mega-fire frequency while satisfying density and budget constraints;
- show seed spread/uncertainty;
- refuse final efficacy, SOC-control, publication-grade, public-policy, or real-wildfire claims.

## Demo read-out

MVP demo:

- side-by-side unmanaged/no-op, best rule baseline, and RL policy;
- visible forest grid;
- selected treatment zones;
- fire spread and tree regrowth;
- metrics panel;
- fire-size distribution.

Demo claim:

> In this toy model, the learned policy reduced catastrophic cascades versus simple baselines under the declared constraints.

Non-claims:

- no real wildfire prediction;
- no real land-management recommendation;
- no final SOC-control proof;
- no publication-grade science claim.

## Relationship to earlier docs

`docs/PRD-zone-control-rl-mvp.md` is the current requirements spine.

`docs/PRD-real-ffm-environment.md` remains useful for unmanaged environment physics, cluster measurement, reproducibility, and baseline smoke discipline.

`docs/PRD-switch-point-ranger-efficacy.md` is parked as diagnostic/prototype infrastructure. It should not drive new implementation slices unless a future issue explicitly asks for diagnostics.
