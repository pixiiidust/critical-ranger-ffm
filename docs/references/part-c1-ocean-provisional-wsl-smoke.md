# Part C1 Provisional Ocean Smoke: Jamie WSL / GTX 1070

This is operator guidance for Jamie's local WSL/GTX 1070 machine only. Do not run Puffer build/train/eval commands on the VPS.

The C1 slice is provisional/supercritical scaffolding: small debug grid, dummy reward, flat `grid_width * grid_height + no-op` action space, and random-action smoke before the real environment/reward/science lock.

## Status from the 2026-06-09 local smoke

C1 was proven on Jamie's local WSL / GTX 1070 for:

- CUDA/toolchain discovery: GTX 1070, driver `560.94`, CUDA Toolkit `12.6`, `clang`, and `g++-13`.
- Standalone PufferLib local build with `--float --local`.
- C1 self-test and random-action demo.
- Puffer native extension build with `--float`.
- Puffer GPU train smoke to `8.2K` steps.
- Eval checkpoint loading from `latest`.

C1 was not a render proof. The local `binding.c` shim used for the train smoke has a no-op `c_render`, and PufferLib 4.0 `eval()` loops forever by design. A timed eval-load smoke should therefore use `timeout` and treat checkpoint load plus no immediate crash as the useful signal.

## VPS-safe authored-code checks

Run these on the VPS or locally:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

This compiles the provisional C skeleton with `cc` and runs CPU-only self-tests. It does not invoke Puffer, GPU, train, eval, or render.

## Local WSL terminal note

If VS Code's integrated terminal shows no output from interactive WSL commands, first confirm WSL outside VS Code:

```powershell
wsl --set-default Ubuntu-24.04
wsl --cd ~ -e bash -lc 'echo OUTSIDE_VSCODE_WSL_OK; pwd'
```

In the 2026-06-09 smoke, WSL was healthy outside VS Code. The reliable route was to run commands from an external PowerShell / Windows Terminal using `wsl --cd ... --exec /usr/bin/env -i ...` so Windows PATH entries with spaces did not break Bash parsing.

## Local PufferLib 4.0 layout requirements

This PufferLib 4.0 checkout expects envs at:

```text
ocean/<env_name>/<env_name>.c
ocean/<env_name>/binding.c
config/<env_name>.ini
```

Important differences from the first draft of this smoke doc:

- `puffer train` in this checkout does not accept `--local` or `--config`.
- `puffer train <env_name>` loads config from `pufferlib/config/**/*.ini`.
- `bash build.sh <env_name> --float --local` builds the standalone local binary only.
- `puffer train <env_name>` uses the native Python extension, so it also needs `bash build.sh <env_name> --float`.
- `puffer eval` is an infinite loop in `pufferlib/pufferl.py`; use `timeout` for smoke checks.

## Local-only C1 wiring used for the 2026-06-09 smoke

From Jamie's local WSL workspace:

```bash
cd ~/puffer-work
mkdir -p pufferlib/ocean/critical_ranger_ffm
cp critical-ranger-ffm/src/critical_ranger_ffm/ocean/ffm_c1_ocean_provisional.c \
  pufferlib/ocean/critical_ranger_ffm/critical_ranger_ffm.c
cp critical-ranger-ffm/src/critical_ranger_ffm/ocean/ffm_c1_ocean_provisional.h \
  pufferlib/ocean/critical_ranger_ffm/ffm_c1_ocean_provisional.h
```

The copied `critical_ranger_ffm.c` needed the demo entrypoint enabled for standalone local build:

```c
#define FFM_C1_PROVISIONAL_DEMO 1
```

The train smoke also required a local `ocean/critical_ranger_ffm/binding.c` shim and `config/critical_ranger_ffm.ini`. These were local proof artifacts, not a final repo implementation.

The local config used for the smoke was:

```ini
[base]
env_name = critical_ranger_ffm

[vec]
total_agents = 128

[train]
total_timesteps = 8192
```

`total_agents = 128` satisfied Puffer's default validation because `minibatch_size 8192 <= total_agents 128 * horizon 64`.

## Clean environment wrapper for Jamie's WSL / GTX 1070

Use a clean env wrapper from external PowerShell / Windows Terminal to avoid Windows PATH quoting issues:

```powershell
wsl --cd /home/jamie_sim/puffer-work/pufferlib --exec /usr/bin/env -i HOME=/home/jamie_sim PATH=/home/jamie_sim/puffer-work/venv/bin:/usr/local/cuda-12.6/bin:/usr/bin:/bin:/usr/sbin:/sbin:/usr/lib/wsl/lib CUDA_HOME=/usr/local/cuda-12.6 CUDA_PATH=/usr/local/cuda-12.6 LD_LIBRARY_PATH=/home/jamie_sim/puffer-work/cuda-wheel-lib:/usr/local/cuda-12.6/lib64:/usr/lib/wsl/lib LIBRARY_PATH=/home/jamie_sim/puffer-work/cuda-wheel-lib:/usr/local/cuda-12.6/lib64:/usr/lib/wsl/lib CC=clang CXX=g++-13 CUDAHOSTCXX=/usr/bin/g++-13 NVCC_PREPEND_FLAGS=--compiler-bindir=/usr/bin/g++-13 /bin/bash -lc '<COMMAND>'
```

Replace `<COMMAND>` with the local command to run.

## Proven local smoke commands/results

### 1. Standalone local build

```bash
bash build.sh critical_ranger_ffm --float --local
```

Observed result:

```text
Compiling critical_ranger_ffm...
Built: ./critical_ranger_ffm
BUILD_EXIT:0
```

### 2. Self-test

```bash
./critical_ranger_ffm --self-test
```

Observed result:

```text
c1 provisional self-test: PASS
SELF_TEST_EXIT:0
```

### 3. Random-action demo with C1 provisional config

```bash
./critical_ranger_ffm \
  --config /home/jamie_sim/puffer-work/critical-ranger-ffm/configs/ffm_c1_ocean_provisional.ini \
  --demo-steps 4096
```

Observed result:

```text
C1 provisional random-action demo
grid=32x32 actions=1025 obs=3072 steps=4096 saw_cell=1 saw_noop=1 effective_interventions=3481
DEMO_EXIT:0
```

### 4. Native extension build for Puffer train

```bash
bash build.sh critical_ranger_ffm --float
```

Observed result:

```text
Compiling static library for critical_ranger_ffm...
Compiling CUDA (native) training backend...
Built: pufferlib/_C.cpython-312-x86_64-linux-gnu.so
EXT_BUILD_EXIT:0
```

### 5. Puffer train smoke

```bash
timeout 90s puffer train critical_ranger_ffm
```

Observed result included:

```text
Detected discrete action space with 1 heads
Env              critical_ranger_ffm
Steps                           8.2K
SPS                            21.8K
VRAM: 1.7/8G
TRAIN_EXIT:0
```

### 6. Eval-load smoke

```bash
timeout 45s puffer eval critical_ranger_ffm --load-model-path latest --render-mode None --eval-episodes 1
```

Observed result:

```text
Detected discrete action space with 1 heads
Loaded weights from checkpoints/critical_ranger_ffm/1781045599516/0000000000008192.bin
EVAL_1EP_EXIT:124
```

`124` is the expected `timeout` exit when Puffer's eval loop keeps running. In this checkout, `pufferlib/pufferl.py` contains:

```python
while True:
    backend.render(pufferl, 0)
    backend.rollouts(pufferl)
```

So the eval smoke should not be treated as a bounded completion test unless a separate bounded eval harness is added.

## Success criteria for C1 local smoke

C1 local smoke passes when:

- The GTX 1070/CUDA 12.6 toolchain is visible from Ubuntu 24.04 WSL.
- `bash build.sh critical_ranger_ffm --float --local` exits `0`.
- `./critical_ranger_ffm --self-test` exits `0`.
- The random-action demo reports `actions = grid_width * grid_height + 1`, sees both cell actions and no-op, and exits `0`.
- `bash build.sh critical_ranger_ffm --float` builds `pufferlib/_C*.so` for `critical_ranger_ffm`.
- `timeout 90s puffer train critical_ranger_ffm` exits `0` after a short GPU smoke.
- `timeout ... puffer eval ... --load-model-path latest` loads the checkpoint and does not crash before timeout.

Out of scope for C1:

- Real renderer.
- Real reward quality.
- SOC/fire-size science gates.
- Freezing arena constants.
- Restoring C0.1 slope/repeatability gates.
- C0.2 science sweep conclusions.

## Next engineering implication

The next slice should not polish this shim. It should build the real environment according to the project specs:

1. Implement the unmanaged FFM physics and standalone C demo first.
2. Add HK cluster sizing and CSV logging.
3. Run baseline smoke to find real `p/f`, critical density, and episode length.
4. Only after the unmanaged baseline produces SOC-like monster fires, feed measured numbers back into config/reporting.
5. Then add the agent/reward/Puffer training path as a proper binding, not a provisional shim.
