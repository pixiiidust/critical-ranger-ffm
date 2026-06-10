# PRD: Zone-Control RL MVP

## Problem Statement

The switch-point single-cell efficacy path produced useful infrastructure, but it is too brittle to remain the main roadmap. The density-matched single-cell gate exposed geometry and matching confounds: a tiny local counterfactual can become a test of edge/corner sampling rather than a test of forest control.

The project now needs a clearer MVP question:

Can reinforcement learning reduce mega-fire frequency in a toy self-organized forest-fire model better than honest simple baselines, while preserving acceptable forest density and staying within an intervention budget?

This PRD supersedes `docs/PRD-switch-point-ranger-efficacy.md` as the main roadmap. The switch-point work is parked as diagnostic/prototype infrastructure, not deleted.

## Solution

Build a zone-control RL MVP around repeated management decisions over a forest-fire grid:

- use zones as the intervention unit, not individual cells;
- let the agent choose no-op or thin exactly one zone per decision tick;
- compare the learned policy against simple rule baselines under the same seeds, budget, and measurement contract;
- judge success by mega-fire reduction subject to forest-density and intervention-cost constraints;
- keep reward, evaluation, and demo read-out separate so training score does not become a fake science claim.

This PRD is a planning artifact. It does not create implementation issues, start coding, run training, run Puffer/GPU/eval/render work, or publish efficacy/SOC/policy claims.

## User Stories

1. As Jamie, I want the project roadmap to pivot from single-cell switch-point efficacy to zone-control RL, so that the main proof matches the actual forest-management thesis.
2. As Jamie, I want the old switch-point path preserved as diagnostic infrastructure, so that useful runner/reporting lessons are not thrown away.
3. As Jamie, I want zone-level actions for V1, so that the agent manages connected fuel regions instead of overfitting to one-cell counterfactuals.
4. As Jamie, I want a no-op action, so that the policy can learn when intervention is unnecessary.
5. As Jamie, I want exactly one zone-thinning action per decision tick, so that V1 stays interpretable and budgetable.
6. As Jamie, I want prescribed burns, firebreak construction, suppression, and multi-action budgets deferred, so that action semantics do not swamp the first experiment.
7. As Jamie, I want the primary success read-out to be mega-fire frequency reduction, so that the experiment targets catastrophic cascades rather than cosmetic short-term score.
8. As Jamie, I want forest-density constraints attached to the primary metric, so that the agent cannot win by clearing the forest.
9. As Jamie, I want intervention-cost constraints attached to the primary metric, so that the agent cannot win by spending unlimited treatment.
10. As Jamie, I want RL compared against honest simple baselines, so that a learned policy only matters if it beats obvious rules.
11. As Jamie, I want no-action baseline results, so that unmanaged behavior remains visible.
12. As Jamie, I want random-zone thinning baseline results, so that the learned policy beats chance under the same budget.
13. As Jamie, I want densest-zone thinning baseline results, so that the learned policy beats a simple fuel-load heuristic.
14. As Jamie, I want largest-cluster-edge thinning baseline results, so that the learned policy beats a simple connectivity heuristic.
15. As Jamie, I want fixed-firebreak/grid-pattern baseline results, so that the learned policy beats a static human-readable layout.
16. As Jamie, I want periodic thinning baseline results, so that the learned policy beats a simple schedule.
17. As Jamie, I want reward terms that penalize burned area and mega-fires, so that training points toward the evaluation goal.
18. As Jamie, I want reward terms that penalize treatment cost and over-clearing, so that the policy cannot game the environment by destroying fuel everywhere.
19. As Jamie, I want density health terms in the reward, so that the policy is nudged toward a living forest rather than an empty one.
20. As Jamie, I want reward weights treated as provisional, so that early tuning does not become the scientific claim.
21. As Jamie, I want evaluation metrics reported separately from reward, so that score hacking is visible.
22. As Jamie, I want evaluation across multiple seeds and environment parameters, so that one lucky run does not become the result.
23. As Jamie, I want side-by-side visualization of unmanaged, best-rule baseline, and RL policy behavior, so that the demo explains the control story.
24. As Jamie, I want metric panels for mega-fires, burn area, density, and cost, so that the visual demo stays tied to evidence.
25. As Jamie, I want fire-size distribution read-outs, so that catastrophic-tail behavior remains visible.
26. As Jamie, I want explicit non-claims, so that the MVP stays honest about toy-model scope and avoids policy/publication overreach.

## Implementation Decisions

- The zone-control RL MVP is now the main roadmap. The switch-point single-cell efficacy PRD is parked as diagnostic/prototype infrastructure.
- V1 actions are exactly no-op or thin one selected zone per decision tick.
- V1 does not include prescribed burns, active suppression, multi-zone actions, adaptive firebreak construction, homes/value maps, wind, slope, moisture, or real geography.
- V1 should use a grid-and-zone layout that is large enough to show spatial structure but small enough to train and debug. A practical first target is a `64x64` forest divided into an `8x8` zone grid, yielding `64` selectable zones plus no-op. A `100x100` forest with `10x10` zones remains a later/demo-scale option if training and visualization cost are acceptable.
- Cell states remain categorical: empty, tree, burning, and treated/firebreak/thinned representation as needed by the zone-thinning semantics.
- Zone thinning is the sole active intervention in V1. Its exact cell-level effect should be deterministic and budget-accounted, then tested separately before training.
- The agent acts at a fixed decision interval rather than every physics tick. The interval is a tunable environment parameter, with the first PRD-level intent being slow management decisions rather than twitch fire suppression.
- Observations should start from zone summaries rather than full flat cell-action assumptions: tree density by zone, burning density by zone, treated/thinned density by zone, recent fire size, largest connected fuel cluster or cluster-risk summary, elapsed time/steps, and budget/cost state.
- Full-grid visual/state data may still be used internally, for rendering, diagnostics, or later CNN observations, but V1 product/evidence language centers zone control.
- The primary success metric is mega-fire frequency reduction versus the strongest simple baseline, subject to acceptable average tree density, minimum tree density, and intervention budget/cost constraints.
- Supporting evaluation metrics include max fire size, total burned area, fire-size distribution, average tree density, minimum tree density, intervention cost, and budget utilization.
- The MVP baseline set is: no action, random zone thinning, densest-zone thinning, largest-cluster-edge zone thinning, fixed firebreak/grid pattern, and periodic thinning. Periodic prescribed burn is deferred unless V1 explicitly adds burn actions later.
- Reward and success read-out are separate. Reward is for learning; the primary success metric is for belief.
- Initial reward shape should include penalties for burned area, mega-fire events, treatment cost, low-density collapse, and over-clearing, plus a bounded bonus or penalty band for healthy density. Reduced-cluster-risk reward is allowed only if it is treated as shaping, not the final proof.
- Anti-cheat constraints must be first-class: policies that reduce mega-fires by emptying the forest, spending unlimited treatment, exploiting reset conditions, or only delaying catastrophe beyond the episode horizon should fail the read-out.
- Evaluation should use shared seed schedules across RL and baselines where practical, fixed budgets, fixed decision intervals, and predeclared reporting fields.
- The first demo/eval read-out should compare unmanaged/no-op, best simple rule baseline, and RL side by side with the same seed or comparable seed batch. It should show the forest grid, selected treatment zones, fire spread/regrowth, and metric panels.
- Treat the demo as a toy control environment and explanation tool, not real wildfire prediction, real land-management guidance, or publication-grade SOC proof.

## Testing Decisions

- Test external behavior and contracts before training. Do not use training results to discover whether the environment semantics are correct.
- Add deterministic fixture tests for zone indexing, no-op behavior, zone-thinning effects, treatment-cost accounting, and decision-interval timing.
- Add tests that thinning one zone cannot accidentally mutate other zones.
- Add tests that budget/cost state updates exactly once per decision action.
- Add tests that no-op has no treatment cost and no direct grid mutation.
- Add tests for observation contracts: zone densities, burning density, treated/thinned density, recent fire size, cluster-risk summaries, and budget/cost fields have stable shapes and ranges.
- Add tests for baseline policies using small known grids: random-zone action shape, densest-zone selection, largest-cluster-edge selection, fixed-grid pattern selection, and periodic-thinning schedule.
- Add report/fixture tests for the evaluation summary: mega-fire count/frequency, max fire size, total burned area, fire-size distribution, average/minimum density, and intervention cost.
- Add anti-cheat tests or report assertions that flag forest-clearing wins, over-budget wins, and density-collapse wins as invalid success.
- Keep VPS verification CPU-only: docs/static/unit/fixture tests are allowed; Puffer/GPU/train/eval/native render/raylib/`c_render` commands are not.
- Local WSL/GPU runtime gates remain human-approved and one command at a time. No larger local run should start from this PRD without explicit approval.

## Evidence Gates

### Gate 1: Zone-control environment contract

Passing this gate proves the environment and action contracts are wired, not that RL works.

Required:

- no-op and one-zone-thinning actions exist;
- zone indexing is deterministic and documented;
- decision interval is enforced;
- treatment cost/budget is tracked;
- observations expose stable zone summaries;
- fixture tests pass.

### Gate 2: Baseline evaluation contract

Passing this gate proves honest comparisons can be run, not that RL wins.

Required:

- no-action, random-zone, densest-zone, largest-cluster-edge, fixed-firebreak/grid-pattern, and periodic-thinning baselines exist or are explicitly stubbed with failing tests before implementation;
- all baselines run under the same budget, seed schedule, decision interval, and report schema;
- reports include mega-fire frequency, max fire size, total burned area, fire-size distribution, density metrics, and cost metrics;
- forest-clearing and over-budget outcomes are visible as failures, not wins.

### Gate 3: First RL-vs-baseline MVP read-out

Counts only as toy-environment MVP evidence.

Required:

- RL is compared against the strongest simple baseline, not only no-op;
- RL reduces mega-fire frequency while staying within density and budget constraints;
- uncertainty or seed-spread is shown;
- no final efficacy, SOC-control, publication-grade, public-policy, or real-wildfire claim is made.

## Out of Scope

- Creating implementation issues before Jamie approves this PRD direction.
- Starting coding or training from this PRD without a separate approval gate.
- Running Puffer/GPU/train/eval/native render/raylib/`c_render` on the VPS.
- Running larger local WSL gates without Jamie's explicit approval.
- Editing `README.md` or `docs/PRD.md` without explicit instruction.
- Overwriting existing PRDs.
- Deleting switch-point artifacts or pretending prior work was wasted.
- Final efficacy claims.
- Final SOC-control claims.
- Publication-grade science claims.
- Policy-quality or real-world wildfire-management claims.
- Real maps, homes/value maps, wind, slope, moisture, operational suppression, or real land-management prescriptions.
- Multi-agent rangers, animated ranger avatar mechanics, or advanced visualization polish beyond the first evidence read-out.

## Further Notes

### Resolved pivot decisions

1. The zone-control RL MVP formally supersedes the switch-point single-cell efficacy PRD as the main roadmap.
2. Switch-point work is preserved as diagnostic/prototype infrastructure only.
3. V1 action model is no-op plus one-zone thinning per decision tick.
4. Primary success metric is mega-fire frequency reduction versus the strongest simple baseline, subject to density and intervention-budget constraints.
5. Baselines must include no-action, random-zone thinning, densest-zone thinning, largest-cluster-edge zone thinning, fixed-firebreak/grid-pattern, and periodic thinning.
6. Reward must penalize burned area, mega-fires, treatment cost, low-density collapse, and over-clearing, while preserving a healthy density band.
7. First demo/eval read-out should be side-by-side unmanaged/no-op, best rule baseline, and RL, with metric panels and fire-size distribution.

### Pushback / risks to watch

- Biggest risk: the primary metric can still be gamed unless density floors, budget caps, and episode horizons are enforced as hard read-out constraints.
- The strongest baseline may be surprisingly good. That is a feature, not a problem; RL should earn its keep.
- Zone summaries may hide fine-grained connectivity that matters. If learning stalls, add richer observation channels before adding more action types.
- Fixed zones may create boundary artifacts. Keep this visible in reports and consider shifted/multi-scale zones only after V1 proves the comparison loop.
- Reward shaping can become a second brittle measuring stick. Keep the belief update on evaluation metrics, not reward score.

### Relationship to prior PRDs

`docs/PRD-real-ffm-environment.md` remains useful as the unmanaged environment and measurement spine.

`docs/PRD-switch-point-ranger-efficacy.md` is no longer the main roadmap. It remains a diagnostic/prototype reference for replay discipline, reporting contracts, non-claims, and evidence-gate hygiene.
