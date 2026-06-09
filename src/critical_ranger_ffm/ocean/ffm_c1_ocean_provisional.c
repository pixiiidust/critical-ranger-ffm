// Critical Ranger FFM C1 provisional Ocean/Puffer binding skeleton.
// CPU-only authored-code slice: no Puffer headers, no train/eval/render path.

#include "ffm_c1_ocean_provisional.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define FFM_C1_MAX_LINE 512

static void *ffm_c1_xcalloc(size_t n, size_t size) {
    void *ptr = calloc(n, size);
    if (!ptr) {
        fprintf(stderr, "ERROR: allocation failed\n");
        exit(1);
    }
    return ptr;
}

static uint64_t ffm_c1_next_u64(FfmC1Rng *rng) {
    uint64_t z = (rng->state += 0x9E3779B97F4A7C15ULL);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}

static double ffm_c1_unit(FfmC1Rng *rng) {
    return (ffm_c1_next_u64(rng) >> 11) * (1.0 / 9007199254740992.0);
}

static int ffm_c1_idx(int row, int col, int width) {
    return row * width + col;
}

static int ffm_c1_has_burning_neighbor(const unsigned char *grid, int r, int c, int w, int h) {
    if (r > 0 && grid[ffm_c1_idx(r - 1, c, w)] == FFM_C1_BURNING) return 1;
    if (r + 1 < h && grid[ffm_c1_idx(r + 1, c, w)] == FFM_C1_BURNING) return 1;
    if (c > 0 && grid[ffm_c1_idx(r, c - 1, w)] == FFM_C1_BURNING) return 1;
    if (c + 1 < w && grid[ffm_c1_idx(r, c + 1, w)] == FFM_C1_BURNING) return 1;
    return 0;
}

FfmC1Config ffm_c1_default_config(void) {
    FfmC1Config cfg;
    cfg.grid_width = 32;
    cfg.grid_height = 32;
    cfg.p = 0.01;
    cfg.f = 0.000001;
    cfg.seed = 20260609ULL;
    cfg.initial_tree_density = 0.55;
    cfg.episode_step_cap = 256;
    cfg.dummy_reward = 0.0f;
    return cfg;
}

int ffm_c1_validate_config(const FfmC1Config *cfg) {
    if (!cfg) return 0;
    if (cfg->grid_width <= 0 || cfg->grid_height <= 0) return 0;
    if (cfg->p < 0.0 || cfg->p > 1.0 || cfg->f < 0.0 || cfg->f > 1.0) return 0;
    if (cfg->initial_tree_density < 0.0 || cfg->initial_tree_density > 1.0) return 0;
    if (cfg->episode_step_cap <= 0) return 0;
    return 1;
}

int ffm_c1_init(FfmC1Env *env, const FfmC1Config *cfg) {
    if (!env || !ffm_c1_validate_config(cfg)) return 0;
    memset(env, 0, sizeof(*env));
    env->cfg = *cfg;
    env->rng.state = cfg->seed;
    env->cell_count = cfg->grid_width * cfg->grid_height;
    env->action_count = env->cell_count + 1;
    env->obs_count = env->cell_count * FFM_C1_OBS_CHANNELS;
    env->grid = (unsigned char *)ffm_c1_xcalloc((size_t)env->cell_count, sizeof(unsigned char));
    env->next = (unsigned char *)ffm_c1_xcalloc((size_t)env->cell_count, sizeof(unsigned char));
    env->obs = (float *)ffm_c1_xcalloc((size_t)env->obs_count, sizeof(float));
    for (int i = 0; i < env->cell_count; i++) {
        env->grid[i] = ffm_c1_unit(&env->rng) < cfg->initial_tree_density ? FFM_C1_TREE : FFM_C1_EMPTY;
    }
    ffm_c1_write_observation(env);
    return 1;
}

void ffm_c1_free(FfmC1Env *env) {
    if (!env) return;
    free(env->obs);
    free(env->next);
    free(env->grid);
    memset(env, 0, sizeof(*env));
}

FfmC1DecodedAction ffm_c1_decode_action(int action, int grid_width, int grid_height) {
    FfmC1DecodedAction decoded;
    decoded.row = -1;
    decoded.col = -1;
    decoded.is_noop = 0;
    decoded.is_valid = 0;
    if (grid_width <= 0 || grid_height <= 0 || action < 0) return decoded;

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

int ffm_c1_random_action(FfmC1Rng *rng, int action_count) {
    if (!rng || action_count <= 0) return 0;
    return (int)(ffm_c1_next_u64(rng) % (uint64_t)action_count);
}

void ffm_c1_write_observation(FfmC1Env *env) {
    if (!env || !env->obs || !env->grid) return;
    memset(env->obs, 0, (size_t)env->obs_count * sizeof(float));
    for (int i = 0; i < env->cell_count; i++) {
        unsigned char state = env->grid[i];
        if (state <= FFM_C1_BURNING) env->obs[i * FFM_C1_OBS_CHANNELS + state] = 1.0f;
    }
}

FfmC1StepResult ffm_c1_step(FfmC1Env *env, int action) {
    FfmC1StepResult result;
    memset(&result, 0, sizeof(result));
    if (!env || !env->grid || !env->next || !env->obs) return result;

    FfmC1DecodedAction decoded = ffm_c1_decode_action(action, env->cfg.grid_width, env->cfg.grid_height);
    if (decoded.is_valid && !decoded.is_noop) {
        int at = ffm_c1_idx(decoded.row, decoded.col, env->cfg.grid_width);
        if (env->grid[at] == FFM_C1_TREE) {
            env->grid[at] = FFM_C1_EMPTY;
            result.effective_intervention = 1;
        }
    }

    for (int i = 0; i < env->cell_count; i++) {
        if (env->grid[i] == FFM_C1_EMPTY && ffm_c1_unit(&env->rng) < env->cfg.p) {
            env->grid[i] = FFM_C1_TREE;
        }
        if (env->grid[i] == FFM_C1_TREE && ffm_c1_unit(&env->rng) < env->cfg.f) {
            env->grid[i] = FFM_C1_BURNING;
            result.lightning_ignitions++;
        }
    }

    result.active_after = 0;
    for (int r = 0; r < env->cfg.grid_height; r++) {
        for (int c = 0; c < env->cfg.grid_width; c++) {
            int at = ffm_c1_idx(r, c, env->cfg.grid_width);
            unsigned char state = env->grid[at];
            if (state == FFM_C1_BURNING) {
                env->next[at] = FFM_C1_EMPTY;
            } else if (state == FFM_C1_TREE && ffm_c1_has_burning_neighbor(env->grid, r, c, env->cfg.grid_width, env->cfg.grid_height)) {
                env->next[at] = FFM_C1_BURNING;
                result.active_after++;
            } else {
                env->next[at] = state;
            }
        }
    }

    memcpy(env->grid, env->next, (size_t)env->cell_count * sizeof(unsigned char));
    env->step_count++;
    result.reward = env->cfg.dummy_reward;
    result.truncated = env->step_count >= env->cfg.episode_step_cap;
    ffm_c1_write_observation(env);
    return result;
}

static int ffm_c1_assert_true(int condition, const char *name) {
    if (!condition) fprintf(stderr, "self-test failed: %s\n", name);
    return condition;
}

int ffm_c1_run_random_demo(const FfmC1Config *cfg, int steps) {
    FfmC1Env env;
    if (!ffm_c1_init(&env, cfg)) return 1;
    int saw_cell_action = 0;
    int saw_noop_action = 0;
    int effective_interventions = 0;

    for (int i = 0; i < steps; i++) {
        int action = ffm_c1_random_action(&env.rng, env.action_count);
        FfmC1DecodedAction decoded = ffm_c1_decode_action(action, env.cfg.grid_width, env.cfg.grid_height);
        if (decoded.is_noop) saw_noop_action = 1;
        else if (decoded.is_valid) saw_cell_action = 1;
        FfmC1StepResult result = ffm_c1_step(&env, action);
        if (result.effective_intervention) effective_interventions++;
    }

    printf("C1 provisional random-action demo\n");
    printf("grid=%dx%d actions=%d obs=%d steps=%d saw_cell=%d saw_noop=%d effective_interventions=%d\n",
           env.cfg.grid_width,
           env.cfg.grid_height,
           env.action_count,
           env.obs_count,
           env.step_count,
           saw_cell_action,
           saw_noop_action,
           effective_interventions);
    ffm_c1_free(&env);
    return saw_cell_action && saw_noop_action ? 0 : 1;
}

int ffm_c1_run_self_tests(void) {
    int ok = 1;

    FfmC1DecodedAction first = ffm_c1_decode_action(0, 4, 3);
    FfmC1DecodedAction last = ffm_c1_decode_action(11, 4, 3);
    FfmC1DecodedAction noop = ffm_c1_decode_action(12, 4, 3);
    FfmC1DecodedAction invalid = ffm_c1_decode_action(13, 4, 3);
    ok &= ffm_c1_assert_true(first.is_valid && first.row == 0 && first.col == 0, "first action decodes to first cell");
    ok &= ffm_c1_assert_true(last.is_valid && last.row == 2 && last.col == 3, "last cell action decodes to bottom-right cell");
    ok &= ffm_c1_assert_true(noop.is_valid && noop.is_noop, "cell_count action decodes to no-op");
    ok &= ffm_c1_assert_true(!invalid.is_valid, "above no-op action is invalid");

    FfmC1Config cfg = ffm_c1_default_config();
    cfg.grid_width = 3;
    cfg.grid_height = 3;
    cfg.p = 0.0;
    cfg.f = 0.0;
    cfg.initial_tree_density = 0.0;
    cfg.episode_step_cap = 20;
    FfmC1Env env;
    ok &= ffm_c1_assert_true(ffm_c1_init(&env, &cfg), "env init");
    for (int i = 0; i < env.cell_count; i++) env.grid[i] = FFM_C1_TREE;
    env.grid[0] = FFM_C1_TREE;
    env.grid[4] = FFM_C1_BURNING;
    env.grid[8] = FFM_C1_EMPTY;
    env.obs[0] = 99.0f;
    ffm_c1_write_observation(&env);
    ok &= ffm_c1_assert_true(env.obs[0 * FFM_C1_OBS_CHANNELS + FFM_C1_TREE] == 1.0f, "tree one-hot index set");
    ok &= ffm_c1_assert_true(env.obs[4 * FFM_C1_OBS_CHANNELS + FFM_C1_BURNING] == 1.0f, "burning one-hot index set");
    ok &= ffm_c1_assert_true(env.obs[8 * FFM_C1_OBS_CHANNELS + FFM_C1_EMPTY] == 1.0f, "empty one-hot index set");
    ok &= ffm_c1_assert_true(env.obs[0 * FFM_C1_OBS_CHANNELS + FFM_C1_EMPTY] == 0.0f, "observation zeroed before write");

    env.grid[8] = FFM_C1_TREE;
    FfmC1StepResult stepped = ffm_c1_step(&env, 9);
    ok &= ffm_c1_assert_true(stepped.active_after == 4, "snapshot spread ignites exactly orthogonal neighbors");
    ok &= ffm_c1_assert_true(env.grid[4] == FFM_C1_EMPTY, "snapshot burning cell burns out");
    ok &= ffm_c1_assert_true(env.grid[1] == FFM_C1_BURNING && env.grid[3] == FFM_C1_BURNING &&
                             env.grid[5] == FFM_C1_BURNING && env.grid[7] == FFM_C1_BURNING,
                             "orthogonal neighbors become burning");
    ffm_c1_free(&env);

    FfmC1Rng action_rng = { 20260609ULL };
    int saw_cell = 0;
    int saw_noop = 0;
    int action_count = 17;
    for (int i = 0; i < 512; i++) {
        int action = ffm_c1_random_action(&action_rng, action_count);
        if (action == action_count - 1) saw_noop = 1;
        else if (action >= 0 && action < action_count - 1) saw_cell = 1;
    }
    ok &= ffm_c1_assert_true(saw_cell && saw_noop, "random action path covers cell actions and no-op");

    if (ok) {
        printf("c1 provisional self-test: PASS\n");
        return 0;
    }
    return 1;
}

#ifdef FFM_C1_PROVISIONAL_DEMO
static void ffm_c1_trim(char *s) {
    char *start = s;
    while (*start == ' ' || *start == '\t' || *start == '\r' || *start == '\n') start++;
    if (start != s) memmove(s, start, strlen(start) + 1);
    size_t len = strlen(s);
    while (len > 0 && (s[len - 1] == ' ' || s[len - 1] == '\t' || s[len - 1] == '\r' || s[len - 1] == '\n')) {
        s[--len] = '\0';
    }
}

static void ffm_c1_set_config(FfmC1Config *cfg, const char *key, const char *value) {
    if (strcmp(key, "grid_width") == 0) cfg->grid_width = atoi(value);
    else if (strcmp(key, "grid_height") == 0) cfg->grid_height = atoi(value);
    else if (strcmp(key, "p") == 0) cfg->p = atof(value);
    else if (strcmp(key, "f") == 0) cfg->f = atof(value);
    else if (strcmp(key, "seed") == 0) cfg->seed = strtoull(value, NULL, 10);
    else if (strcmp(key, "initial_tree_density") == 0) cfg->initial_tree_density = atof(value);
    else if (strcmp(key, "episode_step_cap") == 0) cfg->episode_step_cap = atoi(value);
    else if (strcmp(key, "dummy_reward") == 0) cfg->dummy_reward = (float)atof(value);
}

static int ffm_c1_load_config_file(FfmC1Config *cfg, const char *path) {
    FILE *fp = fopen(path, "r");
    if (!fp) return 0;
    char line[FFM_C1_MAX_LINE];
    while (fgets(line, sizeof(line), fp)) {
        ffm_c1_trim(line);
        if (line[0] == '\0' || line[0] == '#') continue;
        char *eq = strchr(line, '=');
        if (!eq) continue;
        *eq = '\0';
        char *key = line;
        char *value = eq + 1;
        ffm_c1_trim(key);
        ffm_c1_trim(value);
        ffm_c1_set_config(cfg, key, value);
    }
    fclose(fp);
    return 1;
}

int main(int argc, char **argv) {
    FfmC1Config cfg = ffm_c1_default_config();
    int self_test = 0;
    int demo_steps = 4096;
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--self-test") == 0) {
            self_test = 1;
        } else if (strcmp(argv[i], "--config") == 0 && i + 1 < argc) {
            if (!ffm_c1_load_config_file(&cfg, argv[++i])) {
                fprintf(stderr, "ERROR: could not open config file\n");
                return 1;
            }
        } else if (strcmp(argv[i], "--demo-steps") == 0 && i + 1 < argc) {
            demo_steps = atoi(argv[++i]);
        } else {
            fprintf(stderr, "ERROR: unknown or incomplete argument\n");
            return 1;
        }
    }
    if (self_test) return ffm_c1_run_self_tests();
    return ffm_c1_run_random_demo(&cfg, demo_steps);
}
#endif
