# Switch-Point Test Protocol

Issue #18 defines the protocol for the first switch-point read-out from the baseline evidence. This is protocol/planning only. It is not the paired-experiment runner, not a training redesign, and not a policy-quality or final-science claim.

## Question

At a candidate intervention moment, did the ranger-chosen intervention produce a better counterfactual outcome than a density-matched control intervention at the same timestep?

The unit of comparison is a pair:

- treatment: the ranger-chosen intervention cell;
- control: one density-matched control cell selected from the same pre-intervention grid at the same timestep;
- both branches start from the same pre-intervention grid and environment state.

This keeps the protocol focused on the marginal effect of the chosen cell, not on broad differences between unrelated episodes.

## Pair construction

For each eligible sample:

1. Roll the environment to a sampled decision timestep using the candidate baseline/ranger setup.
2. Save the complete pre-intervention state before the action is applied.
3. Record the ranger-chosen intervention cell.
4. Select a density-matched control cell from the same pre-intervention grid at the same timestep.
5. Create two branches from the saved state:
   - treatment branch applies the ranger-chosen intervention;
   - control branch applies the density-matched control intervention.
6. Run both branches through the same read-out window and compare paired outcomes.

Density matching should be defined before implementation. The default matching variable is local fuel/tree density around the candidate cell, binned tightly enough to avoid comparing a frontier action against an obviously different empty or saturated region. If no valid density-matched control exists for a sample, mark the pair invalid instead of silently relaxing the match.

## RNG and replay contract

A valid pair must share the stochastic future after the intervention point:

- shared seed for the pair;
- same pre-intervention grid;
- same post-intervention lightning/regrowth sequence;
- same sampled lightning cells in both branches;
- same regrowth draws in both branches.

The only intended difference between the branches is the intervention cell. If branch code consumes random numbers differently, implementation must use a replay tape or equivalent deterministic schedule so the post-intervention lightning/regrowth sequence remains shared.

## Frozen-policy read-out

The policy is frozen after the intervention for the switch-point read-out window.

For this protocol, frozen means:

- no further learning during the paired read-out;
- no adaptive second intervention that reacts differently in treatment vs control;
- no online update of the policy, value model, or intervention rule during the branch comparison;
- the same fixed read-out rule and horizon apply to both branches.

The read-out window should be long enough to observe near-term divergence from the intervention but short enough that the pair remains interpretable as a local switch-point test. The exact horizon belongs in the approved implementation plan, not in this protocol slice.

## Outcomes and success criteria

The primary result should be a paired contrast, not two unrelated aggregate means. Candidate outcome families may include living-tree fraction, burned-area avoided, time-to-large-fire, or downstream cluster statistics, but the protocol must report them as paired differences with uncertainty.

Do not optimize on a single noisy fire-size metric. Fire size can be reported as a supporting diagnostic, but it must not be the only decision rule because individual fires are noisy, heavy-tailed, and sensitive to the exact lightning sequence.

A useful first signal is directional consistency across paired samples and seeds: the ranger branch should improve the pre-declared paired outcome more often or by a larger paired mean/median than the density-matched control branch. The protocol should also report invalid-pair rate and density-match quality so a positive result cannot hide poor controls.

## Sample counts

Use 100 paired samples as a signal check only. It can catch obvious wiring mistakes or a very large directional effect, but it is not enough to update belief strongly.

Require several hundred paired samples across many seeds before belief. Samples should be distributed across many independent seeds/episodes, not harvested from one long rollout as if they were independent.

If the 100-pair signal check is inconsistent, stop and inspect matching, RNG sharing, read-out horizon, and outcome definitions before scaling up.

## Stop conditions

Stop or quarantine a sample when any of these occur:

- no valid density-matched control exists at the same timestep;
- treatment and control branches do not share the same post-intervention lightning/regrowth sequence;
- the policy is not frozen after the intervention;
- the pair is drawn from a state outside the approved baseline candidate settings;
- branch replay changes anything except the intervention cell.

Stop the experiment-design escalation when the protocol itself is still under review. Do not create implementation issues until Jamie approves this protocol.

## Scope guardrails

- This is HITL protocol/planning only.
- Implementation of paired rollout runners is out of scope until Jamie approves this protocol.
- Do not create implementation issues until Jamie approves this protocol.
- Publication-grade SOC proof is out of scope.
- A policy-quality claim is out of scope.
- Do not claim that baseline smoke output proves criticality.
- Do not run Puffer, GPU, train, eval, render, raylib, or `c_render` work on the VPS from this protocol.
- Do not edit `README.md` or `docs/PRD.md` for this slice.

## Review checklist

Before any follow-up implementation issue exists, Jamie should approve or change:

- the density matching variable and bin width;
- the read-out horizon;
- the primary paired outcome;
- the invalid-pair handling rule;
- the seed/sample schedule for the 100-pair signal check and later several-hundred-pair belief run.
