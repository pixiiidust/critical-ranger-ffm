// PufferLib 4.0 Ocean wrapper for the Critical Ranger FFM C1 binding.
// This file adapts the CPU-tested real binding seam to Puffer's vecenv.h API.

#ifndef CRITICAL_RANGER_FFM_PUFFER_OCEAN_H
#define CRITICAL_RANGER_FFM_PUFFER_OCEAN_H

#include <string.h>

#include "ffm_c1_ocean_binding.h"

typedef struct {
    float perf;
    float score;
    float episode_return;
    float episode_length;
    float effective_interventions;
    float n;
} Log;

typedef struct {
    Log log;
    float *observations;
    float *actions;
    float *rewards;
    float *terminals;
    int num_agents;
    unsigned int rng;
    FfmC1OceanEnv ocean;
    FfmC1OceanConfig cfg;
    int initialized;
    float current_return;
    float current_length;
} CriticalRangerFfm;

static void critical_ranger_ffm_copy_observation(CriticalRangerFfm *env) {
    if (!env || !env->observations || !env->ocean.obs) return;
    memcpy(env->observations, env->ocean.obs, (size_t)env->ocean.obs_count * sizeof(float));
}

static void critical_ranger_ffm_close_inner(CriticalRangerFfm *env) {
    if (!env || !env->initialized) return;
    ffm_c1_ocean_free(&env->ocean);
    env->initialized = 0;
}

void c_reset(CriticalRangerFfm *env) {
    if (!env) return;
    critical_ranger_ffm_close_inner(env);
    env->cfg = ffm_c1_ocean_default_config();
    if (env->rng != 0) env->cfg.ffm.seed = (uint64_t)env->rng;
    if (!ffm_c1_ocean_init(&env->ocean, &env->cfg)) {
        env->initialized = 0;
        if (env->terminals) env->terminals[0] = 1.0f;
        if (env->rewards) env->rewards[0] = 0.0f;
        return;
    }
    env->initialized = 1;
    env->current_return = 0.0f;
    env->current_length = 0.0f;
    if (env->terminals) env->terminals[0] = 0.0f;
    if (env->rewards) env->rewards[0] = 0.0f;
    critical_ranger_ffm_copy_observation(env);
}

void c_step(CriticalRangerFfm *env) {
    if (!env) return;
    if (!env->initialized) c_reset(env);
    if (!env->initialized) return;

    int action = env->actions ? (int)env->actions[0] : env->ocean.action_count - 1;
    FfmC1OceanStepResult step = ffm_c1_ocean_step(&env->ocean, action);

    env->rewards[0] = step.reward;
    env->terminals[0] = step.truncated ? 1.0f : 0.0f;
    env->current_return += step.reward;
    env->current_length += 1.0f;
    env->log.perf += step.reward;
    env->log.score += step.reward;
    env->log.episode_return += env->current_return;
    env->log.episode_length += env->current_length;
    env->log.effective_interventions += step.effective_intervention ? 1.0f : 0.0f;
    env->log.n += 1.0f;

    critical_ranger_ffm_copy_observation(env);
    if (step.truncated) {
        // Issue #17: Puffer's terminal flag is a cap/reset signal here,
        // not terminal success/failure or a policy-quality judgment.
        float truncated_reward = step.reward;
        c_reset(env);
        if (env->terminals) env->terminals[0] = 1.0f;
        if (env->rewards) env->rewards[0] = truncated_reward;
    }
}

#ifndef CRITICAL_RANGER_FFM_HAS_RAYLIB_RENDER
#if defined(CRITICAL_RANGER_FFM_ENABLE_RAYLIB_RENDER)
#define CRITICAL_RANGER_FFM_HAS_RAYLIB_RENDER 1
#elif defined(__has_include)
#if __has_include("raylib.h")
#define CRITICAL_RANGER_FFM_HAS_RAYLIB_RENDER 1
#endif
#endif
#endif

#ifdef CRITICAL_RANGER_FFM_HAS_RAYLIB_RENDER
#ifndef CRITICAL_RANGER_FFM_RAYLIB_TEST_STUB
#include "raylib.h"
#endif
#endif

#ifndef CRITICAL_RANGER_FFM_RENDER_CELL_PX
#define CRITICAL_RANGER_FFM_RENDER_CELL_PX 4
#endif

void c_render(CriticalRangerFfm *env) {
#ifndef CRITICAL_RANGER_FFM_HAS_RAYLIB_RENDER
    (void)env;
    // Issue #20 optional render path is compile-gated so CPU/Puffer builds without raylib stay safe.
#else
    if (!env || !env->initialized || !env->ocean.ffm.grid) return;

    const int cell_px = CRITICAL_RANGER_FFM_RENDER_CELL_PX;
    const int width = env->ocean.ffm.cfg.grid_width;
    const int height = env->ocean.ffm.cfg.grid_height;
    const Color empty_color = {80, 80, 80, 255};
    const Color tree_color = {0, 160, 64, 255};
    const Color burning_color = {255, 128, 0, 255};
    const Color unknown_color = {200, 0, 200, 255};
    const Color outline_color = {24, 24, 24, 255};

    BeginDrawing();
    ClearBackground(BLACK);
    for (int row = 0; row < height; row++) {
        for (int col = 0; col < width; col++) {
            int idx = row * width + col;
            Color color = unknown_color;
            unsigned char state = env->ocean.ffm.grid[idx];
            if (state == CR_FFM_EMPTY) color = empty_color;
            else if (state == CR_FFM_TREE) color = tree_color;
            else if (state == CR_FFM_BURNING) color = burning_color;

            int x = col * cell_px;
            int y = row * cell_px;
            DrawRectangle(x, y, cell_px, cell_px, color);
            DrawRectangleLines(x, y, cell_px, cell_px, outline_color);
        }
    }
    EndDrawing();
#endif
}

void c_close(CriticalRangerFfm *env) {
    critical_ranger_ffm_close_inner(env);
}

#endif
