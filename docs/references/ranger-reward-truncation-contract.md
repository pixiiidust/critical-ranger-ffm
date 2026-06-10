# Ranger reward and truncation contract

Issue #17 records the first training-facing reward and reset contract for the real Critical Ranger FFM Puffer/Ocean binding.

## Reward contract

The V1 ranger reward is a rolling discounted living-tree fraction:

`reward_t = gamma * reward_{t-1} + (1 - gamma) * living_tree_fraction_t`

where `living_tree_fraction_t` is the post-step count of `CR_FFM_TREE` cells divided by total cells. The value is normalized to [0, 1] when `gamma` is in `(0, 1]` and the stored prior reward starts at `0` on reset.

Scope guardrails:

- No stay-near-criticality reward is included in V1.
- No intervention cost is included in V1 unless Jamie changes the PRD later.
- Effective interventions can reduce future reward only through the resulting grid state, not through a direct action penalty.
- Spatial style, cluster shape, SOC quality, and policy taste are not reward terms in this slice.

## Truncation and reset contract

Episode caps are truncations, not terminal success/failure. The unmanaged FFM is a continuing process with a bounded rollout window for training and logging hygiene. In short: episode caps are truncations.

For the Puffer wrapper:

- `FfmC1OceanStepResult.truncated` mirrors the unmanaged environment cap.
- The Puffer terminal flag is a reset signal when the cap is reached.
- The wrapper resets the inner environment after a truncation so the next step starts a fresh rollout window.
- The cap signal is not terminal success/failure and does not judge policy quality.
- Reward at the truncation step remains the normalized contract reward, not a success/failure bonus.

## What this does not prove

This contract does not judge policy quality, train a final agent, redesign observations/actions, or make final science claims about criticality. It only makes reward scale and reset semantics explicit and CPU-testable.

Do not run Puffer, GPU, train, eval, or render commands on the VPS for this slice. CPU-only compile/unit/static tests are sufficient here.
