# Part C0 Baseline Smoke Demo

Part C0 is unmanaged FFM physics only. It intentionally excludes ranger actions, reward code, Puffer/Ocean training, and GPU commands.

## What it measures

The standalone C demo writes Part B-compatible `cluster-close` CSV rows from an unmanaged forest-fire model:

- `0=empty`, `1=tree`, `2=burning`
- regrowth probability `p`
- lightning probability `f`
- synchronous snapshot fire spread to orthogonal / 4-neighbor tree cells
- snapshot-burning cells burn out to empty in the same update
- burned-mask tracking during an active quiet-window event
- 4-neighbor Hoshen-Kopelman-style connected-component labeling when the grid goes quiet

## Measurement-size rule

Fast tests may override the grid to `32x32`, but numbers carried forward into the experiment must come from `128x128` or larger.

The default config pins:

```text
grid_width=128
grid_height=128
min_gate_grid_size=128
```

The summary reports `measurement_grid_gate`. Treat `warn` as a test/debug run only, not as a valid baseline measurement.

The measured critical density may differ from textbook/literature FFM values; for this project it describes this frozen implementation arena and is not a canonical SOC density/exponent claim.

## Frozen arena rule

Part C0.1 freezes the arena constants shared by baseline and future agent comparisons. These must not change between comparison runs:

- `grid_width`
- `grid_height`
- `min_gate_grid_size`
- `connectivity`
- `p`
- `f`
- `warmup_steps`

The frozen reference is `configs/ffm_arena.frozen.ini`. Future agent/eval configs must match it; `compare_arena_constants` in `critical_ranger_ffm.baseline.repeatability` is the guard helper.

## Warm-up rule

Critical-density estimates use only post-warm-up global tree density samples. Part C0 uses a fixed generous warm-up cutoff from config:

```text
warmup_steps=10000
```

The summary prints:

- `warmup_steps_used`
- `density_samples_after_warmup`
- `critical_density_mean`
- `critical_density_band_min`
- `critical_density_band_max`

This makes the density estimate auditable and avoids silently measuring the initial transient.

## Repeatability gate

The baseline is accepted as a stable comparison arena only if a same-constants seed sweep passes hard thresholds. The default Part C0.1 gate runs `128x128` with `cluster_target=2000` for each seed and fails if spread is too wide:

- critical-density mean range across seeds must be `<= 0.01`
- fitted-slope range across seeds must be `<= 0.08`
- each seed must retain `>= 1.5` fire-size orders of magnitude
- max multi-component quiet-window rate must be `<= 0.10`

The fitted slope is computed one canonical way: `critical_ranger_ffm.reporting.report_fire_sizes.fit_slope`. Baseline repeatability and future agent comparison must use that shared helper, not an equivalent reimplementation.

## Commands

Build:

```bash
cc -std=c11 -O2 -Wall -Wextra -pedantic demos/ffm_baseline_smoke.c -lm -o /tmp/ffm_baseline_smoke
```

Run built-in physics checks:

```bash
/tmp/ffm_baseline_smoke --self-test
```

Run the default 128x128 measurement-size smoke:

```bash
/tmp/ffm_baseline_smoke --config configs/ffm_baseline_smoke.ini
```

Run the Part C0.1 repeatability sweep:

```bash
PYTHONPATH=src python3 -m critical_ranger_ffm.baseline.repeatability \
  --seeds 20260609,20260610,20260611 \
  --out-dir reports/part-c0-1-repeatability
```

Reporter round-trip:

```bash
PYTHONPATH=src python3 -m critical_ranger_ffm.reporting.report_fire_sizes \
  --clusters data/fixtures/part_c0_baseline_clusters.csv \
  --interventions data/fixtures/intervention_sample.csv \
  --config configs/reporting.default.json \
  --out-dir reports/part-c0-baseline-smoke/reporter
```

## Interpreting gate warnings

Expect p/f iteration. A first failed gate is not proof the idea is wrong.

- Too few fires: raise `f` or run longer.
- Tail truncated / no large fires: lower `f/p`.
- Too much overlap: lower `f`.
- If `128x128` cannot show `>=1.5` orders of magnitude at reasonable `f/p`, treat that as a finite-size signal to test larger grids later, not automatically as a physics bug.
