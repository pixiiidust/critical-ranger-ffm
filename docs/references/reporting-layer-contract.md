# Reporting Layer Contract — Part B

> Status: legacy switch-point/reporting reference. Keep this contract for prior paired-intervention reporting and fixture discipline. New zone-control evaluation/reporting work should be defined under the zone-control RL MVP issue sequence and should not treat density-matched single-cell intervention rows as the main evidence path.

Part B is reporting-only. It defines the CSV surface and plotting behavior before the custom C/Ocean forest-fire environment exists.

This slice must not change environment physics. The future C/Ocean implementation only needs to emit rows matching this contract.

## Buildable now vs contract-only

Buildable now:

- CSV validation.
- Synthetic/sample fixture rows.
- Baseline/agent log-log plotting against fixture data.
- Paired intervention shift plotting against fixture data.
- Summary-table printing.
- Small-sample warnings instead of crashes.

Contract-only until the custom env and frozen policy exist:

- Real `agent` rows.
- Real `ranger_intervention` rows.
- Real `density_matched_control` rows.
- Scientific claims about switch points.

## Cluster-close CSV

One row per closed fire cluster after quiet-window Hoshen-Kopelman labeling.

Required columns:

- `schema_version`
- `run_id`
- `mode`: `baseline`, `agent`, `ranger_intervention`, or `density_matched_control`
- `seed`
- `episode_id`
- `step`
- `event_id`
- `cluster_id`
- `fire_size`: whole-fire connected burned component size, not per-step burn count
- `grid_width`
- `grid_height`
- `p`
- `f`
- `global_tree_density`
- `quiet_window_component_count`
- `pair_id`: empty for baseline/ordinary agent rows; shared by ranger/control paired rows
- `source`: `synthetic`, `env`, or `eval`
- `notes`

## Intervention CSV

One row per ranger/control intervention point. Downstream cluster rows link back through `pair_id`.

Required columns:

- `schema_version`
- `pair_id`
- `run_id`
- `mode`: `ranger_intervention` or `density_matched_control`
- `seed`
- `episode_id`
- `intervention_step`
- `action_row`
- `action_col`
- `selected_cell_state`: `empty`, `tree`, or `burning`
- `effective_intervention`: `true` only when the selected cell was `tree`
- `local_fuel_density`
- `density_bucket`: `low`, `mid`, or `high` density tercile
- `matched_control_for_pair_id`
- `post_intervention_seed`
- `downstream_window_steps`
- `source`
- `notes`

## Required validity checks

Density matching is part of the contract, not decoration.

For every complete ranger/control pair:

- `pair_id` must link one `ranger_intervention` row and one `density_matched_control` row.
- ranger and control `density_bucket` values must match.
- mismatched density buckets are flagged with a warning and excluded from the shift plot.
- post-intervention seeds should match; mismatches are warned because paired rollout noise would contaminate the comparison.

Effective-intervention semantics are also enforced:

- `selected_cell_state=tree` requires `effective_intervention=true`.
- `selected_cell_state=empty` or `burning` requires `effective_intervention=false`.
- non-effective interventions are warned and excluded from shift aggregation by default.

This protects the switch-point comparison from silently averaging unmatched controls or no-op actions.

## Reporter command

From the repo root:

```bash
PYTHONPATH=src python3 -m critical_ranger_ffm.reporting.report_fire_sizes \
  --clusters data/fixtures/cluster_close_sample.csv \
  --interventions data/fixtures/intervention_sample.csv \
  --config configs/reporting.default.json \
  --out-dir reports/part-b-smoke
```

Expected outputs:

- `reports/part-b-smoke/fire_size_loglog.png`
- `reports/part-b-smoke/intervention_shift.png`
- stdout summary table with slopes, sample counts, and steps-to-critical-like per mode
- warnings for provisional/small-sample data

## Steps-to-critical-like

For Part B, `steps-to-critical-like` is provisional:

> first step/window where the run has a stable heavy-tail fit and fitted slope inside the baseline-derived acceptable slope band for N consecutive windows.

Because no real baseline smoke-test artifact has locked N or slope band yet, the defaults live in `configs/reporting.default.json`:

- `min_clusters_for_fit`: 50
- `min_orders_of_magnitude`: 1.5
- `steps_window_size`: 10000
- `consecutive_windows_required`: 3
- `baseline_slope_band_half_width`: 0.25
- `provisional_results`: true

Once the unmanaged measurement smoke test exists, replace the provisional slope band with the baseline-derived band.

## W&B note

Puffer supports one-flag live training graphs:

```bash
puffer train <env_name> --wandb
```

That is separate from this CSV reporting path and should not be wired into C environment physics.
