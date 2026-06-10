# Puffer eval render proof protocol (Issue #20)

Issue #20 adds an optional raylib render path for the real Critical Ranger FFM Puffer/Ocean environment. This is a render/debug slice only.

## What changed

- `c_render` now has a compile-gated optional raylib render path.
- The default CPU/VPS build remains safe when raylib is not available.
- When enabled, the render path draws the categorical grid states:
  - empty cells as dark gray
  - tree cells as green
  - burning cells as orange
  - unknown/future states as magenta, leaving room for a future ranger intervention marker if available
- The render loop reads the current grid only and does not change physics, RNG, reward, truncation, or logged outputs.

## Proof boundaries

Keep these three proofs separate:

1. Train smoke from Issue #16
   - Proved native build/buffer/train wiring on Jamie's local WSL / GTX 1070.
   - Reported `EXT_BUILD_EXIT:0`, `TRAIN_EXIT:0`, `8.2K` steps, and `effective_interventions`.
   - It was not visual render proof.

2. checkpoint-load smoke
   - If run, this only proves a bounded eval/checkpoint path loads without an immediate crash.
   - It is not visual render proof unless the raylib window visibly renders the grid.

3. visual render proof
   - Must show a raylib window for the real Critical Ranger FFM environment.
   - The visible grid must distinguish empty, tree, and burning cells clearly.
   - Any future ranger intervention marker must be documented separately when the environment exposes one.

## Local WSL protocol

Do not run Puffer, GPU, train, eval, or render commands on the VPS.

Jamie's local WSL / GTX 1070 render smoke must be requested one command at a time. The pasted output should be recorded in the Issue #20 PR or issue comment before merge.

For review, record:

- the exact local command Jamie ran
- whether the raylib window opened
- whether empty/tree/burning states were visually distinguishable
- whether the command exited cleanly, timed out intentionally, or needed manual close
- a clear note that this remains visual/debug proof, not final science

## Local WSL visual proof received

Jamie verified the Issue #20 direct visual render smoke on local WSL after building raylib in user space and rebuilding/probing the extension with raylib available.

User visual report:

> oh yes i see it now - dark gray, green and orange bands

Observed output markers:

- Raylib initialized successfully with `INFO: Initializing raylib 6.1-dev`.
- Platform backend: `DESKTOP (GLFW)` / X11.
- Render/window size: `384 x 192`.
- Window closed successfully.
- `ISSUE20_RENDER_SMOKE_FRAMES:133`
- `ISSUE20_RENDER_SMOKE_EXIT:0`
- `ISSUE20_RENDER_COMMAND_EXIT:0`

Interpretation: this is visual render proof for the optional Issue #20 debug path. It proves the raylib window can show clearly distinguishable empty/tree/burning categorical states for the real Critical Ranger FFM render code. It is not final science, not train proof, and not a checkpoint-quality claim.

## Current VPS verification

CPU-safe VPS tests can compile the render path with a raylib test stub. That proves categorical draw calls and render isolation without launching Puffer, GPU, eval, train, or a real window on the VPS.
