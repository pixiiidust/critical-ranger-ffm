// Critical Ranger FFM C1 Ocean/Puffer binding around the real FFM environment.
// CPU-safe authored-code seam: this file is compile-tested without invoking Puffer/GPU.

#include "ffm_c1_ocean_binding.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void *ffm_c1_ocean_xcalloc(size_t n, size_t size) {
    void *ptr = calloc(n, size);
    if (!ptr) {
        fprintf(stderr, "ERROR: allocation failed\n");
        exit(1);
    }
    return ptr;
}

FfmC1OceanConfig ffm_c1_ocean_default_config(void) {
    FfmC1OceanConfig cfg;
    cfg.ffm = cr_ffm_default_config();
    cfg.ffm.grid_width = 128;
    cfg.ffm.grid_height = 128;
    cfg.ffm.p = 0.01;
    cfg.ffm.f = 0.000001;
    cfg.ffm.seed = 20260610ULL;
    cfg.ffm.initial_tree_density = 0.55;
    cfg.ffm.episode_step_cap = 200000;
    cfg.ffm.connectivity = CR_FFM_CONNECTIVITY_4;
    cfg.gamma = 0.99f;
    return cfg;
}

int ffm_c1_ocean_validate_config(const FfmC1OceanConfig *cfg) {
    if (!cfg) return 0;
    if (!cr_ffm_validate_config(&cfg->ffm)) return 0;
    if (cfg->gamma <= 0.0f || cfg->gamma > 1.0f) return 0;
    return 1;
}

int ffm_c1_ocean_init(FfmC1OceanEnv *env, const FfmC1OceanConfig *cfg) {
    if (!env || !ffm_c1_ocean_validate_config(cfg)) return 0;
    memset(env, 0, sizeof(*env));
    if (!cr_ffm_init(&env->ffm, &cfg->ffm)) return 0;
    env->action_count = env->ffm.cell_count + 1;
    env->obs_count = env->ffm.cell_count * FFM_C1_OCEAN_OBS_CHANNELS;
    env->obs = (float *)ffm_c1_ocean_xcalloc((size_t)env->obs_count, sizeof(float));
    ffm_c1_ocean_write_observation(env);
    return 1;
}

void ffm_c1_ocean_free(FfmC1OceanEnv *env) {
    if (!env) return;
    free(env->obs);
    env->obs = NULL;
    cr_ffm_free(&env->ffm);
    memset(env, 0, sizeof(*env));
}

FfmC1OceanDecodedAction ffm_c1_ocean_decode_action(int action, int grid_width, int grid_height) {
    FfmC1OceanDecodedAction decoded;
    decoded.row = -1;
    decoded.col = -1;
    decoded.is_noop = 0;
    decoded.is_valid = 0;
    if (grid_width <= 0 || grid_height <= 0 || action < 0) return decoded;
    if (grid_width > 0 && grid_height > 2147483647 / grid_width) return decoded;

    int cell_count = grid_width * grid_height;
    if (action == cell_count) {
        decoded.is_noop = 1;
        decoded.is_valid = 1;
        return decoded;
    }
    if (action < cell_count) {
        decoded.row = action / grid_width;
        decoded.col = action % grid_width;
        decoded.is_valid = 1;
    }
    return decoded;
}

void ffm_c1_ocean_write_observation(FfmC1OceanEnv *env) {
    if (!env || !env->obs || !env->ffm.grid) return;
    memset(env->obs, 0, (size_t)env->obs_count * sizeof(float));
    for (int i = 0; i < env->ffm.cell_count; i++) {
        unsigned char state = env->ffm.grid[i];
        if (state <= CR_FFM_BURNING) {
            env->obs[i * FFM_C1_OCEAN_OBS_CHANNELS + state] = 1.0f;
        }
    }
}

static int ffm_c1_ocean_count_trees(const FfmC1OceanEnv *env) {
    int trees = 0;
    for (int i = 0; i < env->ffm.cell_count; i++) {
        if (env->ffm.grid[i] == CR_FFM_TREE) trees++;
    }
    return trees;
}

FfmC1OceanStepResult ffm_c1_ocean_step(FfmC1OceanEnv *env, int action) {
    FfmC1OceanStepResult result;
    memset(&result, 0, sizeof(result));
    if (!env || !env->ffm.grid || !env->obs) return result;

    FfmC1OceanDecodedAction decoded = ffm_c1_ocean_decode_action(
        action,
        env->ffm.cfg.grid_width,
        env->ffm.cfg.grid_height
    );
    if (decoded.is_valid && !decoded.is_noop) {
        int at = decoded.row * env->ffm.cfg.grid_width + decoded.col;
        if (env->ffm.grid[at] == CR_FFM_TREE) {
            env->ffm.grid[at] = CR_FFM_EMPTY;
            result.effective_intervention = 1;
        }
    }

    result.ffm = cr_ffm_step_unmanaged(&env->ffm);
    result.truncated = result.ffm.truncated;
    result.reward = env->ffm.cell_count > 0
        ? (float)ffm_c1_ocean_count_trees(env) / (float)env->ffm.cell_count
        : 0.0f;
    ffm_c1_ocean_write_observation(env);
    return result;
}
