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
    cfg.connectivity = CR_FFM_CONNECTIVITY_4;
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
    if (cfg->connectivity != CR_FFM_CONNECTIVITY_4) return 0;
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

static int cr_ffm_config_equal(const CrFfmConfig *a, const CrFfmConfig *b) {
    if (!a || !b) return 0;
    return a->grid_width == b->grid_width &&
           a->grid_height == b->grid_height &&
           a->p == b->p &&
           a->f == b->f &&
           a->seed == b->seed &&
           a->initial_tree_density == b->initial_tree_density &&
           a->episode_step_cap == b->episode_step_cap &&
           a->connectivity == b->connectivity;
}

int cr_ffm_snapshot_init(CrFfmSnapshot *snapshot, const CrFfmEnv *env) {
    if (!snapshot || !env || !env->grid || env->cell_count <= 0) return 0;
    memset(snapshot, 0, sizeof(*snapshot));
    snapshot->cfg = env->cfg;
    snapshot->rng = env->rng;
    snapshot->cell_count = env->cell_count;
    snapshot->step_count = env->step_count;
    snapshot->grid = (unsigned char *)malloc((size_t)env->cell_count * sizeof(unsigned char));
    if (!snapshot->grid) {
        memset(snapshot, 0, sizeof(*snapshot));
        return 0;
    }
    memcpy(snapshot->grid, env->grid, (size_t)env->cell_count * sizeof(unsigned char));
    return 1;
}

void cr_ffm_snapshot_free(CrFfmSnapshot *snapshot) {
    if (!snapshot) return;
    free(snapshot->grid);
    memset(snapshot, 0, sizeof(*snapshot));
}

int cr_ffm_restore(CrFfmEnv *env, const CrFfmSnapshot *snapshot) {
    if (!env || !snapshot || !snapshot->grid || !cr_ffm_validate_config(&snapshot->cfg)) return 0;
    CrFfmEnv restored;
    memset(&restored, 0, sizeof(restored));
    restored.cfg = snapshot->cfg;
    restored.rng = snapshot->rng;
    restored.cell_count = snapshot->cell_count;
    restored.step_count = snapshot->step_count;
    restored.grid = (unsigned char *)malloc((size_t)snapshot->cell_count * sizeof(unsigned char));
    restored.next = (unsigned char *)calloc((size_t)snapshot->cell_count, sizeof(unsigned char));
    if (!restored.grid || !restored.next) {
        free(restored.next);
        free(restored.grid);
        return 0;
    }
    memcpy(restored.grid, snapshot->grid, (size_t)snapshot->cell_count * sizeof(unsigned char));
    cr_ffm_free(env);
    *env = restored;
    return 1;
}

int cr_ffm_env_matches_snapshot(const CrFfmEnv *env, const CrFfmSnapshot *snapshot) {
    if (!env || !snapshot || !env->grid || !snapshot->grid) return 0;
    if (!cr_ffm_config_equal(&env->cfg, &snapshot->cfg)) return 0;
    if (env->rng.state != snapshot->rng.state) return 0;
    if (env->cell_count != snapshot->cell_count) return 0;
    if (env->step_count != snapshot->step_count) return 0;
    return memcmp(env->grid, snapshot->grid, (size_t)env->cell_count * sizeof(unsigned char)) == 0;
}

int cr_ffm_replay_tape_init(CrFfmReplayTape *tape, const CrFfmSnapshot *snapshot, int step_count) {
    if (!tape || !snapshot || !snapshot->grid || snapshot->cell_count <= 0 || step_count <= 0) return 0;
    memset(tape, 0, sizeof(*tape));
    tape->step_count = step_count;
    tape->cell_count = snapshot->cell_count;
    size_t count = (size_t)step_count * (size_t)snapshot->cell_count;
    tape->regrowth_draws = (double *)malloc(count * sizeof(double));
    tape->lightning_draws = (double *)malloc(count * sizeof(double));
    if (!tape->regrowth_draws || !tape->lightning_draws) {
        cr_ffm_replay_tape_free(tape);
        return 0;
    }
    CrFfmRng replay_rng = snapshot->rng;
    for (size_t i = 0; i < count; i++) {
        tape->regrowth_draws[i] = cr_ffm_unit(&replay_rng);
        tape->lightning_draws[i] = cr_ffm_unit(&replay_rng);
    }
    return 1;
}

void cr_ffm_replay_tape_free(CrFfmReplayTape *tape) {
    if (!tape) return;
    free(tape->lightning_draws);
    free(tape->regrowth_draws);
    memset(tape, 0, sizeof(*tape));
}

CrFfmStepResult cr_ffm_step_unmanaged(CrFfmEnv *env) {
    return cr_ffm_step_unmanaged_with_burned_mask(env, NULL);
}

CrFfmStepResult cr_ffm_step_unmanaged_with_burned_mask(CrFfmEnv *env, unsigned char *burned_mask) {
    CrFfmStepResult result;
    memset(&result, 0, sizeof(result));
    if (!env || !env->grid || !env->next) return result;

    int w = env->cfg.grid_width;
    int h = env->cfg.grid_height;
    int n = env->cell_count;
    if (burned_mask) memset(burned_mask, 0, (size_t)n * sizeof(unsigned char));
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
                if (burned_mask) burned_mask[at] = 1;
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

CrFfmStepResult cr_ffm_step_unmanaged_with_replay(CrFfmEnv *env, const CrFfmReplayTape *tape, int replay_step, unsigned char *burned_mask) {
    CrFfmStepResult result;
    memset(&result, 0, sizeof(result));
    if (!env || !env->grid || !env->next || !tape || !tape->regrowth_draws || !tape->lightning_draws) return result;
    if (replay_step < 0 || replay_step >= tape->step_count || env->cell_count != tape->cell_count) return result;

    int w = env->cfg.grid_width;
    int h = env->cfg.grid_height;
    int n = env->cell_count;
    size_t offset = (size_t)replay_step * (size_t)n;
    if (burned_mask) memset(burned_mask, 0, (size_t)n * sizeof(unsigned char));
    result.active_before = cr_ffm_count_state(env->grid, n, CR_FFM_BURNING);

    for (int i = 0; i < n; i++) {
        if (env->grid[i] == CR_FFM_EMPTY && tape->regrowth_draws[offset + (size_t)i] < env->cfg.p) {
            env->grid[i] = CR_FFM_TREE;
            result.regrowths++;
        }
        if (env->grid[i] == CR_FFM_TREE && tape->lightning_draws[offset + (size_t)i] < env->cfg.f) {
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
                if (burned_mask) burned_mask[at] = 1;
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

CrFfmBranchInvariantResult cr_ffm_check_branch_invariant(const CrFfmEnv *treatment, const CrFfmEnv *control, int allowed_mismatch_index) {
    CrFfmBranchInvariantResult result;
    result.valid = 0;
    result.mismatch_count = 0;
    result.first_mismatch = -1;
    result.reason = CR_FFM_BRANCH_INVARIANT_OK;

    if (!treatment || !control || !treatment->grid || !control->grid) {
        result.reason = CR_FFM_BRANCH_INVARIANT_NULL_ENV;
        return result;
    }
    if (!cr_ffm_config_equal(&treatment->cfg, &control->cfg) || treatment->cell_count != control->cell_count) {
        result.reason = CR_FFM_BRANCH_INVARIANT_CONFIG_MISMATCH;
        return result;
    }
    if (treatment->rng.state != control->rng.state) {
        result.reason = CR_FFM_BRANCH_INVARIANT_RNG_MISMATCH;
        return result;
    }
    if (treatment->step_count != control->step_count) {
        result.reason = CR_FFM_BRANCH_INVARIANT_STEP_MISMATCH;
        return result;
    }

    for (int i = 0; i < treatment->cell_count; i++) {
        if (treatment->grid[i] != control->grid[i]) {
            if (result.first_mismatch < 0) result.first_mismatch = i;
            result.mismatch_count++;
            if (i != allowed_mismatch_index) result.reason = CR_FFM_BRANCH_INVARIANT_GRID_MISMATCH;
        }
    }

    if (result.reason == CR_FFM_BRANCH_INVARIANT_OK) {
        result.valid = result.mismatch_count == 0 || result.mismatch_count == 1;
    }
    return result;
}

int cr_ffm_can_label_fire_clusters(const CrFfmEnv *env) {
    if (!env || !env->grid) return 0;
    return cr_ffm_count_state(env->grid, env->cell_count, CR_FFM_BURNING) == 0;
}

static int cr_ffm_hk_find(int *parent, int x) {
    int root = x;
    while (parent[root] != root) root = parent[root];
    while (parent[x] != x) {
        int next = parent[x];
        parent[x] = root;
        x = next;
    }
    return root;
}

static void cr_ffm_hk_union(int *parent, int a, int b) {
    int root_a = cr_ffm_hk_find(parent, a);
    int root_b = cr_ffm_hk_find(parent, b);
    if (root_a == root_b) return;
    if (root_a < root_b) {
        parent[root_b] = root_a;
    } else {
        parent[root_a] = root_b;
    }
}

int cr_ffm_hk_label_burned_mask(const unsigned char *burned_mask,
                                int width,
                                int height,
                                int connectivity,
                                int *labels,
                                int *component_sizes,
                                int max_components,
                                CrFfmClusterSummary *summary) {
    if (!summary) return 0;
    memset(summary, 0, sizeof(*summary));
    if (!burned_mask || width <= 0 || height <= 0) return 0;
    if (width > 46340 || height > 46340) return 0;
    if (width > 0 && height > 2147483647 / width) return 0;
    if (connectivity != CR_FFM_CONNECTIVITY_4) return 0;

    int n = width * height;
    int *parent = (int *)malloc((size_t)n * sizeof(int));
    int *root_to_component = (int *)malloc((size_t)n * sizeof(int));
    int *all_sizes = (int *)calloc((size_t)n, sizeof(int));
    if (!parent || !root_to_component || !all_sizes) {
        free(all_sizes);
        free(root_to_component);
        free(parent);
        return 0;
    }

    for (int i = 0; i < n; i++) {
        parent[i] = i;
        root_to_component[i] = -1;
        if (labels) labels[i] = 0;
        if (component_sizes && i < max_components) component_sizes[i] = 0;
    }

    for (int r = 0; r < height; r++) {
        for (int c = 0; c < width; c++) {
            int at = cr_ffm_idx(r, c, width);
            if (!burned_mask[at]) continue;
            summary->total_burned++;
            if (c > 0 && burned_mask[cr_ffm_idx(r, c - 1, width)]) {
                cr_ffm_hk_union(parent, at, cr_ffm_idx(r, c - 1, width));
            }
            if (r > 0 && burned_mask[cr_ffm_idx(r - 1, c, width)]) {
                cr_ffm_hk_union(parent, at, cr_ffm_idx(r - 1, c, width));
            }
        }
    }

    for (int i = 0; i < n; i++) {
        if (!burned_mask[i]) continue;
        int root = cr_ffm_hk_find(parent, i);
        int component = root_to_component[root];
        if (component < 0) {
            component = summary->component_count++;
            root_to_component[root] = component;
        }
        if (labels) labels[i] = component + 1;
        all_sizes[component]++;
    }

    for (int i = 0; i < summary->component_count; i++) {
        if (all_sizes[i] > summary->largest_component_size) {
            summary->largest_component_size = all_sizes[i];
        }
        if (component_sizes && i < max_components) {
            component_sizes[i] = all_sizes[i];
            summary->sizes_written++;
        } else if (component_sizes && i >= max_components) {
            summary->overflowed = 1;
        }
    }

    free(all_sizes);
    free(root_to_component);
    free(parent);
    return 1;
}
