#include "ffm_unmanaged.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void *cr_ffm_xcalloc(size_t n, size_t size) {
    void *ptr = calloc(n, size);
    if (!ptr) {
        fprintf(stderr, "ERROR: allocation failed\n");
        exit(1);
    }
    return ptr;
}

static uint64_t cr_ffm_next_u64(CrFfmRng *rng) {
    uint64_t z = (rng->state += 0x9E3779B97F4A7C15ULL);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}

static double cr_ffm_unit(CrFfmRng *rng) {
    return (cr_ffm_next_u64(rng) >> 11) * (1.0 / 9007199254740992.0);
}

static int cr_ffm_idx(int row, int col, int width) {
    return row * width + col;
}

static int cr_ffm_count_state(const unsigned char *grid, int n, unsigned char state) {
    int count = 0;
    for (int i = 0; i < n; i++) {
        if (grid[i] == state) count++;
    }
    return count;
}

static int cr_ffm_has_burning_neighbor(const unsigned char *grid, int r, int c, int w, int h) {
    if (r > 0 && grid[cr_ffm_idx(r - 1, c, w)] == CR_FFM_BURNING) return 1;
    if (r + 1 < h && grid[cr_ffm_idx(r + 1, c, w)] == CR_FFM_BURNING) return 1;
    if (c > 0 && grid[cr_ffm_idx(r, c - 1, w)] == CR_FFM_BURNING) return 1;
    if (c + 1 < w && grid[cr_ffm_idx(r, c + 1, w)] == CR_FFM_BURNING) return 1;
    return 0;
}

CrFfmConfig cr_ffm_default_config(void) {
    CrFfmConfig cfg;
    cfg.grid_width = 32;
    cfg.grid_height = 32;
    cfg.p = 0.01;
    cfg.f = 0.000001;
    cfg.seed = 20260609ULL;
    cfg.initial_tree_density = 0.55;
    cfg.episode_step_cap = 1000;
    return cfg;
}

int cr_ffm_validate_config(const CrFfmConfig *cfg) {
    if (!cfg) return 0;
    if (cfg->grid_width <= 0 || cfg->grid_height <= 0) return 0;
    if (cfg->grid_width > 46340 || cfg->grid_height > 46340) return 0;
    if (cfg->grid_width > 0 && cfg->grid_height > 2147483647 / cfg->grid_width) return 0;
    if (cfg->p < 0.0 || cfg->p > 1.0) return 0;
    if (cfg->f < 0.0 || cfg->f > 1.0) return 0;
    if (cfg->initial_tree_density < 0.0 || cfg->initial_tree_density > 1.0) return 0;
    if (cfg->episode_step_cap <= 0) return 0;
    return 1;
}

int cr_ffm_init(CrFfmEnv *env, const CrFfmConfig *cfg) {
    if (!env || !cr_ffm_validate_config(cfg)) return 0;
    memset(env, 0, sizeof(*env));
    env->cfg = *cfg;
    env->rng.state = cfg->seed;
    env->cell_count = cfg->grid_width * cfg->grid_height;
    env->grid = (unsigned char *)cr_ffm_xcalloc((size_t)env->cell_count, sizeof(unsigned char));
    env->next = (unsigned char *)cr_ffm_xcalloc((size_t)env->cell_count, sizeof(unsigned char));
    for (int i = 0; i < env->cell_count; i++) {
        env->grid[i] = cr_ffm_unit(&env->rng) < cfg->initial_tree_density ? CR_FFM_TREE : CR_FFM_EMPTY;
    }
    return 1;
}

void cr_ffm_free(CrFfmEnv *env) {
    if (!env) return;
    free(env->next);
    free(env->grid);
    memset(env, 0, sizeof(*env));
}

CrFfmStepResult cr_ffm_step_unmanaged(CrFfmEnv *env) {
    CrFfmStepResult result;
    memset(&result, 0, sizeof(result));
    if (!env || !env->grid || !env->next) return result;

    int w = env->cfg.grid_width;
    int h = env->cfg.grid_height;
    int n = env->cell_count;
    result.active_before = cr_ffm_count_state(env->grid, n, CR_FFM_BURNING);

    for (int i = 0; i < n; i++) {
        if (env->grid[i] == CR_FFM_EMPTY && cr_ffm_unit(&env->rng) < env->cfg.p) {
            env->grid[i] = CR_FFM_TREE;
            result.regrowths++;
        }
        if (env->grid[i] == CR_FFM_TREE && cr_ffm_unit(&env->rng) < env->cfg.f) {
            env->grid[i] = CR_FFM_BURNING;
            result.lightning_ignitions++;
        }
    }

    result.active_after = 0;
    for (int r = 0; r < h; r++) {
        for (int c = 0; c < w; c++) {
            int at = cr_ffm_idx(r, c, w);
            unsigned char state = env->grid[at];
            if (state == CR_FFM_BURNING) {
                env->next[at] = CR_FFM_EMPTY;
            } else if (state == CR_FFM_TREE && cr_ffm_has_burning_neighbor(env->grid, r, c, w, h)) {
                env->next[at] = CR_FFM_BURNING;
                result.active_after++;
            } else {
                env->next[at] = state;
            }
        }
    }

    memcpy(env->grid, env->next, (size_t)n * sizeof(unsigned char));
    env->step_count++;
    result.tree_count = cr_ffm_count_state(env->grid, n, CR_FFM_TREE);
    result.truncated = env->step_count >= env->cfg.episode_step_cap;
    return result;
}
