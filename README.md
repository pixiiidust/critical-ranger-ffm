# Critical Ranger FFM

Zone-control RL toy forest-fire experiment: can an agent reduce mega-fires versus simple baselines without clearing the forest?

## Current direction

Critical Ranger FFM is now centered on the **zone-control RL MVP**.

The current experiment asks:

> Can reinforcement learning reduce mega-fire frequency in a toy self-organized forest-fire model better than honest simple baselines, while preserving acceptable forest density and staying within an intervention budget?

The previous single-cell switch-point efficacy path is parked as diagnostic/prototype infrastructure. It produced useful runner, reporting, replay, matching, and non-claim discipline, but it is no longer the main roadmap.

## MVP shape

V1 should stay small and testable:

- forest-fire grid with categorical cell states;
- zone-level intervention unit;
- action model: no-op or thin exactly one selected zone per decision tick;
- fixed decision interval, not twitch fire suppression;
- zone-summary observations;
- budget/cost accounting;
- evaluation against simple non-RL baselines.

Practical first target from the PRD:

- `64x64` forest grid;
- `8x8` zone grid;
- `64` selectable zones plus no-op.

A `100x100` grid with `10x10` zones remains a later/demo-scale option if training and visualization cost are acceptable.

## Main success metric

Primary read-out:

> Mega-fire frequency reduction versus the strongest simple baseline, subject to acceptable average/minimum tree density and intervention-budget constraints.

Supporting metrics:

- max fire size;
- total burned area;
- fire-size distribution;
- average tree density;
- minimum tree density;
- intervention cost;
- budget utilization.

Reward is for learning. Evaluation metrics decide whether the MVP worked.

## Baselines

RL only matters if it beats honest simple rules under the same seeds, budget, decision interval, and report schema.

V1 baselines:

1. no action;
2. random zone thinning;
3. densest-zone thinning;
4. largest-cluster-edge zone thinning;
5. fixed firebreak/grid-pattern thinning;
6. periodic thinning.

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

- RL is compared against the strongest simple baseline, not only no-op;
- RL reduces mega-fire frequency while satisfying density and budget constraints;
- seed spread/uncertainty is shown;
- no final efficacy, SOC-control, publication-grade, public-policy, or real-wildfire claim is made.

## Current issue tree

The pivot tracker is #53:

- #54 — Add zone-control action contract fixtures
- #55 — Add zone-summary observation and budget contract
- #56 — Add simple zone-baseline policy contracts
- #57 — Add zone-control evaluation report and anti-cheat verdicts
- #58 — Add side-by-side zone-control MVP demo fixture
- #59 — Define first local WSL RL-vs-baseline gate

Start with #54. Do not jump to training before the contract and baseline reporting gates exist.

## Key docs

- `docs/PRD-zone-control-rl-mvp.md` — current requirements spine
- `docs/project-brief.md` — concise project brief
- `docs/references/zone-control-rl-mvp-issue-plan.md` — `/to-issues` decomposition
- `docs/PRD-real-ffm-environment.md` — retained unmanaged environment/measurement spine
- `docs/PRD-switch-point-ranger-efficacy.md` — parked diagnostic/prototype reference

## Guardrails

- Do not run Puffer/GPU/train/eval/native render/raylib/`c_render` on the VPS.
- Do not run larger local WSL gates without Jamie explicitly approving the exact command.
- Do not claim final efficacy, final SOC control, publication-grade science, public-policy quality, or real-wildfire validity.
- Do not delete switch-point artifacts; keep them as diagnostics unless a future issue explicitly says otherwise.

## Verification

CPU-safe repo checks use:

```bash
git diff --check
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

These checks do not run GPU/Puffer/train/eval/render work.
