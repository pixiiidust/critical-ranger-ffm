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
    if (step.truncated) c_reset(env);
}

void c_render(CriticalRangerFfm *env) {
    (void)env;
    // Intentionally no-op for Issue #16. Real raylib/c_render visual proof is Issue #20.
}

void c_close(CriticalRangerFfm *env) {
    critical_ranger_ffm_close_inner(env);
}

#endif
