# PufferLib C1 Real Binding Build Notes

Issue #16 replaces the provisional C1 shim with a real binding seam around `src/critical_ranger_ffm/ffm_unmanaged.c`.

This document records build/train wiring reality for Jamie's local WSL/PufferLib checkout. It is not a final science artifact and it is not visual eval proof.

## Scope

- The binding uses the real unmanaged FFM environment state and step function.
- The managed step applies one ranger intervention before the real unmanaged FFM step.
- Action space remains flat: `grid_width * grid_height + no-op`.
- Observation remains full-resolution one-hot channels for empty/tree/burning cells.
- Reward is only the v1 wiring reward: living-tree fraction after the real environment step.
- Real raylib drawing, `c_render`, and visual eval rendering are deferred to #20.

## PufferLib 4.0 layout

Jamie’s local PufferLib 4.0 checkout expects this shape inside the PufferLib repo:

```text
pufferlib/ocean/critical_ranger_ffm/critical_ranger_ffm.c
pufferlib/ocean/critical_ranger_ffm/binding.c
pufferlib/config/critical_ranger_ffm.ini
```

This repo carries the train config at:

```text
pufferlib/config/critical_ranger_ffm.ini
```

The config is intentionally small for a build/buffer/wiring smoke:

- `env_name = critical_ranger_ffm`
- `total_agents = 128`
- `total_timesteps = 8192`

## Local WSL commands only

Do not run Puffer, GPU, train, eval, or render commands on the VPS. CPU-only compile/unit tests are OK on the VPS.

If a local train smoke is needed, ask Jamie one command at a time and wait for pasted output before deciding the next command.

The expected local command shapes are:

```bash
bash build.sh critical_ranger_ffm --float
```

```bash
puffer train critical_ranger_ffm
```

Important PufferLib 4.0 quirks from the previous local smoke:

- `puffer train critical_ranger_ffm` reads config from `pufferlib/config/critical_ranger_ffm.ini`.
- `puffer train` uses the native extension build, not the standalone local binary.
- GTX 1070 uses `--float` for the native extension build.
- Do not add `--local` or `--config` to `puffer train critical_ranger_ffm`.

## Eval/render guardrails

A bounded eval checkpoint-load smoke, if run later, must use `timeout` and may only be documented as checkpoint-load/no-immediate-crash.

A no-op or missing `c_render` is not visual eval proof. Real eval rendering/raylib/`c_render` visual proof belongs to #20, not Issue #16.
