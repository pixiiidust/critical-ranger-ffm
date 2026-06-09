# PufferLib 4.0 on WSL + GTX 1070

This note records the verified setup used for Critical Ranger FFM Part A: prove PufferLib 4.0 can build, train, and eval a built-in environment before custom forest-fire work begins.

## Verified result

Host topology:

- Hermes/Pixoid runs on the DigitalOcean VPS. That machine has no NVIDIA GPU and should not be used for Puffer training.
- PufferLib GPU work runs on Jamie's local desktop WSL environment.
- Local GPU: NVIDIA GeForce GTX 1070, 8GB VRAM.
- Driver-reported CUDA: 12.6.

Verified gates:

- `torch.cuda.is_available()` returned `True`.
- Torch detected `NVIDIA GeForce GTX 1070`.
- `nvcc` was installed from CUDA Toolkit 12.6 and reported `release 12.6, V12.6.85`.
- `bash build.sh breakout --float` completed successfully after the local fixes below.
- `puffer train breakout` ran on GPU at about `1.5M` SPS and used about `1.9/8G` VRAM.
- `puffer eval breakout --load-model-path latest` rendered successfully.

This closes Part A's built-in-environment PufferLib smoke test.

## Why `--float` matters

The GTX 1070 does not support bf16. Build Puffer/Ocean environments with float precision:

```bash
bash build.sh breakout --float
```

The `puffer train` CLI did not accept `--float` during verification. Build with `--float`, then train normally:

```bash
puffer train breakout
```

Eval also ran normally:

```bash
puffer eval breakout --load-model-path latest
```

For future custom env debugging on this GPU, prefer float builds and local/debug builds where appropriate:

```bash
bash build.sh <env_name> --float
bash build.sh <env_name> --float --local
```

## Working shell setup

From Jamie's local desktop WSL shell:

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
```

Then:

```bash
bash build.sh breakout --float
puffer train breakout
puffer eval breakout --load-model-path latest
```

## Manual setup outline

The PufferTank one-liner assumes a narrow CUDA/Ubuntu setup. This project used manual native setup so PyTorch and CUDA Toolkit match the local WSL GPU stack.

Install system dependencies:

```bash
sudo apt-get update
sudo apt-get install -y \
  curl git build-essential clang \
  htop gdb tmux ccache \
  libomp-dev libglfw3 libgl1-mesa-dev \
  python3.12-dev gcc-13 g++-13 wget
```

Install CUDA Toolkit 12.6 for WSL:

```bash
wget https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update
sudo apt-get install -y cuda-toolkit-12-6
```

Install `uv`, create a Python 3.12 venv, and install PufferLib 4.0:

```bash
cd ~
mkdir -p puffer-work
cd puffer-work

curl -LsSf https://astral.sh/uv/install.sh | sh
. "$HOME/.local/bin/env"
uv venv --python 3.12 venv
. venv/bin/activate

git clone https://github.com/pufferai/pufferlib --branch 4.0
cd pufferlib

uv pip install numpy
uv pip install torch --index-url https://download.pytorch.org/whl/cu126
uv pip install -e .
```

Verify Torch sees the GPU:

```bash
python -c 'import torch, numpy; print("torch", torch.__version__); print("numpy", numpy.__version__); print("cuda available:", torch.cuda.is_available()); print("device:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NONE")'
```

Expected:

```text
cuda available: True
device: NVIDIA GeForce GTX 1070
```

## Local PufferLib 4.0 float patch

PufferLib 4.0 hit this compile error in `--float` mode:

```text
src/kernels.cu(323): error: function "cast_dispatch" has already been defined
```

Cause: with `PRECISION_FLOAT`, `precision_t` is `float`, so these overloads become identical:

```c
cast_dispatch(precision_t* dst, const precision_t* src, ...)
cast_dispatch(precision_t* dst, const float* src, ...)
```

Local patch in `src/kernels.cu`:

```c
#ifndef PRECISION_FLOAT
inline void cast_dispatch(precision_t* dst, const float* src, int n, cudaStream_t stream) {
    cast<<<grid_size(n), BLOCK_SIZE, 0, stream>>>(dst, src, n);
}
#endif
```

Rationale: in float mode, float-to-float copies already use the `precision_t` overload. The `const float*` cast overload is only needed for non-float precision.

## WSL linker fixes

Puffer's CUDA backend links unversioned library names:

- `-lnvidia-ml`
- `-lcudnn`
- `-lnccl`

WSL exposed NVML as a versioned file only. Create a linker symlink:

```bash
sudo ln -sf /usr/lib/wsl/lib/libnvidia-ml.so.1 /usr/local/cuda-12.6/lib64/libnvidia-ml.so
```

The `nvidia-cudnn-cu12` and `nvidia-nccl-cu12` Python wheels supplied versioned shared libraries:

```text
~/puffer-work/venv/lib/python3.12/site-packages/nvidia/cudnn/lib/libcudnn.so.9
~/puffer-work/venv/lib/python3.12/site-packages/nvidia/nccl/lib/libnccl.so.2
```

Create unversioned linker symlinks:

```bash
mkdir -p ~/puffer-work/cuda-wheel-lib

ln -sf ~/puffer-work/venv/lib/python3.12/site-packages/nvidia/cudnn/lib/libcudnn.so.9 \
  ~/puffer-work/cuda-wheel-lib/libcudnn.so

ln -sf ~/puffer-work/venv/lib/python3.12/site-packages/nvidia/nccl/lib/libnccl.so.2 \
  ~/puffer-work/cuda-wheel-lib/libnccl.so
```

Then include that directory first in `LD_LIBRARY_PATH` and `LIBRARY_PATH` as shown above.

## Common failure signatures

### Running on the wrong machine

```text
nvidia-smi: command not found
```

If this appears on the VPS, stop. Puffer GPU work belongs on the local desktop WSL environment.

### Missing CUDA compiler

```text
ccache: error: execute_noreturn of ./bin/nvcc failed: No such file or directory
```

Install CUDA Toolkit 12.6 for WSL and export `CUDA_HOME`, `CUDA_PATH`, and `PATH`.

### Too-new host compiler

```text
unsupported GNU version! gcc versions later than 13 are not supported
```

Use `clang` for Puffer's C compile path and `g++-13` for `nvcc`:

```bash
export CC=clang
export CXX=g++-13
export CUDAHOSTCXX=/usr/bin/g++-13
export NVCC_PREPEND_FLAGS="-ccbin /usr/bin/g++-13"
```

### Missing link libraries

```text
/usr/bin/ld: cannot find -lnccl
/usr/bin/ld: cannot find -lnvidia-ml
/usr/bin/ld: cannot find -lcudnn
```

Create the NVML/cuDNN/NCCL symlinks above and ensure `LIBRARY_PATH` includes the symlink directory.

## Next project step

Part A is complete: install, built-in Breakout build, GPU training, and eval/render all passed. The next proposed project slice should be Part B: the reporting layer only. Keep it separate from C environment physics.

Propose before implementing:

1. CSV fixture rows for cluster-close events and intervention events.
2. Build baseline logging + plotting now against synthetic/sample data; treat agent, ranger-poke, and control-poke modes as contract-only until the custom env and trained/frozen policy exist.
3. A small Python/matplotlib reporting script that reads CSV and outputs:
   - log-log fire-size distributions with fitted slopes for baseline vs agent,
   - ranger intervention vs density-matched control shift with spread/error bars,
   - printed summary table with slopes, sample counts, and steps-to-critical-like per mode,
   - small-sample warnings instead of crashes.
4. For this reporting slice, define `steps-to-critical-like` as the first step/window where the run has a stable heavy-tail fit and fitted slope inside the baseline-derived acceptable slope band for N consecutive windows. If N or the slope band is not yet locked by a baseline smoke-test artifact, expose them as config/defaults and label the result provisional.
5. A note that Puffer supports `--wandb` for live training graphs, separate from the C env and reporting CSV path.
