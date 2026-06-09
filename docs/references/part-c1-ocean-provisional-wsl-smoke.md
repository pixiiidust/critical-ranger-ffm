# Part C1 Provisional Ocean Smoke: Jamie WSL / GTX 1070

This is PR-ready operator guidance for Jamie's local WSL/GTX 1070 machine only. Do not run these Puffer build/train/eval commands on the VPS.

The C1 slice is provisional/supercritical scaffolding: small debug grid, dummy reward, flat `grid_width * grid_height + no-op` action space, and random-action smoke before policy training.

## VPS-safe authored-code checks

Run these on the VPS or locally:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

This compiles the provisional C skeleton with `cc` and runs CPU-only self-tests. It does not invoke Puffer, GPU, train, eval, or render.

## Local WSL / GTX 1070 Puffer smoke

From Jamie's PufferLib 4.0 checkout, build the environment locally with float precision and the local/debug path:

```bash
cd ~/puffer-work/pufferlib
. ../venv/bin/activate

export CUDA_HOME=/usr/local/cuda-12.6
export CUDA_PATH=/usr/local/cuda-12.6
export PATH=/usr/local/cuda-12.6/bin:$PATH
export LD_LIBRARY_PATH=$HOME/puffer-work/cuda-wheel-lib:/usr/local/cuda-12.6/lib64:/usr/lib/wsl/lib:${LD_LIBRARY_PATH:-}
export LIBRARY_PATH=$HOME/puffer-work/cuda-wheel-lib:/usr/local/cuda-12.6/lib64:/usr/lib/wsl/lib:${LIBRARY_PATH:-}
export CC=clang
export CXX=g++-13
export CUDAHOSTCXX=/usr/bin/g++-13
export NVCC_PREPEND_FLAGS="-ccbin /usr/bin/g++-13"

bash build.sh critical_ranger_ffm --float --local
```

Then run a short local train smoke with the C1 provisional config. Do not pass `--float` to `puffer train`; the GTX 1070 float requirement is handled by the build step.

```bash
puffer train critical_ranger_ffm --local --config /path/to/critical-ranger-ffm/configs/ffm_c1_ocean_provisional.ini
```

Eval smoke should also stay local and use the float-built local env:

```bash
puffer eval critical_ranger_ffm --local --load-model-path latest
```

Success looks like:

- Build exits `0` with `bash build.sh critical_ranger_ffm --float --local`.
- No bf16 compile path or CUDA architecture error appears on the GTX 1070.
- Train starts, reports/uses the expected flat action count of `grid_width * grid_height + 1`, and steps the environment without observation-buffer, action-decoding, or NaN crashes.
- Eval loads `latest` and steps/renders the provisional environment.
- Slow or unstable training at larger grids is expected and is not a C1 bug; this config stays small to debug wiring.
- Reward is known-dummy output for this slice; policy quality, SOC behavior, fire-size gates, and C0.2 science sweep results are out of scope.
