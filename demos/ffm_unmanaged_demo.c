// Critical Ranger FFM unmanaged demo smoke.
// CPU-only standalone path around the real unmanaged C seam. No Puffer, GPU, train, or eval.

#include "ffm_unmanaged.h"

#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_LINE 512

typedef struct {
    CrFfmConfig env;
    int smoke_step_cap;
    int debug_every;
} DemoConfig;

static void die(const char *message) {
    fprintf(stderr, "ERROR: %s\n", message);
    exit(1);
}

static DemoConfig demo_default_config(void) {
    DemoConfig cfg;
    cfg.env = cr_ffm_default_config();
    cfg.env.grid_width = 8;
    cfg.env.grid_height = 8;
    cfg.env.p = 0.05;
    cfg.env.f = 0.02;
    cfg.env.seed = 20260610ULL;
    cfg.env.initial_tree_density = 0.55;
    cfg.env.episode_step_cap = 12;
    cfg.smoke_step_cap = 6;
    cfg.debug_every = 2;
    return cfg;
}

static void trim(char *s) {
    char *start = s;
    while (*start == ' ' || *start == '\t' || *start == '\r' || *start == '\n') start++;
    if (start != s) memmove(s, start, strlen(start) + 1);
    size_t len = strlen(s);
    while (len > 0 && (s[len - 1] == ' ' || s[len - 1] == '\t' || s[len - 1] == '\r' || s[len - 1] == '\n')) {
        s[--len] = '\0';
    }
}

static int parse_int_value(const char *value, int *out) {
    char *end = NULL;
    errno = 0;
    long parsed = strtol(value, &end, 10);
    if (errno != 0 || end == value) return 0;
    while (*end == ' ' || *end == '\t' || *end == '\r' || *end == '\n') end++;
    if (*end != '\0' || parsed < INT_MIN || parsed > INT_MAX) return 0;
    *out = (int)parsed;
    return 1;
}

static int parse_u64_value(const char *value, uint64_t *out) {
    char *end = NULL;
    errno = 0;
    unsigned long long parsed = strtoull(value, &end, 10);
    if (errno != 0 || end == value) return 0;
    while (*end == ' ' || *end == '\t' || *end == '\r' || *end == '\n') end++;
    if (*end != '\0') return 0;
    *out = (uint64_t)parsed;
    return 1;
}

static int parse_double_value(const char *value, double *out) {
    char *end = NULL;
    errno = 0;
    double parsed = strtod(value, &end);
    if (errno != 0 || end == value) return 0;
    while (*end == ' ' || *end == '\t' || *end == '\r' || *end == '\n') end++;
    if (*end != '\0') return 0;
    *out = parsed;
    return 1;
}

static void set_config(DemoConfig *cfg, const char *key, const char *value) {
    int parsed_int = 0;
    double parsed_double = 0.0;
    uint64_t parsed_u64 = 0;

    if (strcmp(key, "grid_width") == 0) {
        if (!parse_int_value(value, &parsed_int)) die("invalid integer for grid_width");
        cfg->env.grid_width = parsed_int;
    } else if (strcmp(key, "grid_height") == 0) {
        if (!parse_int_value(value, &parsed_int)) die("invalid integer for grid_height");
        cfg->env.grid_height = parsed_int;
    } else if (strcmp(key, "p") == 0) {
        if (!parse_double_value(value, &parsed_double)) die("invalid probability for p");
        cfg->env.p = parsed_double;
    } else if (strcmp(key, "f") == 0) {
        if (!parse_double_value(value, &parsed_double)) die("invalid probability for f");
        cfg->env.f = parsed_double;
    } else if (strcmp(key, "seed") == 0) {
        if (!parse_u64_value(value, &parsed_u64)) die("invalid unsigned seed");
        cfg->env.seed = parsed_u64;
    } else if (strcmp(key, "initial_tree_density") == 0) {
        if (!parse_double_value(value, &parsed_double)) die("invalid probability for initial_tree_density");
        cfg->env.initial_tree_density = parsed_double;
    } else if (strcmp(key, "episode_step_cap") == 0) {
        if (!parse_int_value(value, &parsed_int)) die("invalid integer for episode_step_cap");
        cfg->env.episode_step_cap = parsed_int;
    } else if (strcmp(key, "smoke_step_cap") == 0) {
        if (!parse_int_value(value, &parsed_int)) die("invalid integer for smoke_step_cap");
        cfg->smoke_step_cap = parsed_int;
    } else if (strcmp(key, "debug_every") == 0) {
        if (!parse_int_value(value, &parsed_int)) die("invalid integer for debug_every");
        cfg->debug_every = parsed_int;
    } else {
        die("unknown unmanaged demo config key");
    }
}

static void load_config_file(DemoConfig *cfg, const char *path) {
    FILE *fp = fopen(path, "r");
    if (!fp) die("could not open config file");
    char line[MAX_LINE];
    while (fgets(line, sizeof(line), fp)) {
        trim(line);
        if (line[0] == '\0' || line[0] == '#') continue;
        char *eq = strchr(line, '=');
        if (!eq) {
            fclose(fp);
            die("invalid config line without '='");
        }
        *eq = '\0';
        char *key = line;
        char *value = eq + 1;
        trim(key);
        trim(value);
        set_config(cfg, key, value);
    }
    fclose(fp);
}

static void parse_args(DemoConfig *cfg, int argc, char **argv) {
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--config") == 0 && i + 1 < argc) {
            load_config_file(cfg, argv[++i]);
        } else if (strncmp(argv[i], "--", 2) == 0 && i + 1 < argc) {
            char key[128];
            snprintf(key, sizeof(key), "%s", argv[i] + 2);
            for (char *p = key; *p; p++) {
                if (*p == '-') *p = '_';
            }
            set_config(cfg, key, argv[++i]);
        } else {
            die("unknown or incomplete argument");
        }
    }
}

static void validate_demo_config(const DemoConfig *cfg) {
    if (!cr_ffm_validate_config(&cfg->env)) die("invalid unmanaged demo config");
    if (cfg->smoke_step_cap <= 0) die("invalid unmanaged demo config: smoke_step_cap must be positive");
    if (cfg->debug_every <= 0) die("invalid unmanaged demo config: debug_every must be positive");
    if (cfg->smoke_step_cap > cfg->env.episode_step_cap) {
        die("invalid unmanaged demo config: smoke_step_cap cannot exceed episode_step_cap");
    }
}

static int count_state(const CrFfmEnv *env, unsigned char state) {
    int count = 0;
    for (int i = 0; i < env->cell_count; i++) {
        if (env->grid[i] == state) count++;
    }
    return count;
}

static void print_counts(const char *prefix, int step, const CrFfmEnv *env) {
    printf("%s%d empty=%d tree=%d burning=%d",
           prefix,
           step,
           count_state(env, CR_FFM_EMPTY),
           count_state(env, CR_FFM_TREE),
           count_state(env, CR_FFM_BURNING));
}

static int run_demo(const DemoConfig *cfg) {
    CrFfmEnv env;
    if (!cr_ffm_init(&env, &cfg->env)) die("failed to initialize unmanaged FFM env");

    printf("Critical Ranger FFM unmanaged demo smoke\n");
    printf("seed=%llu grid=%dx%d p=%.10g f=%.10g episode_step_cap=%d smoke_step_cap=%d\n",
           (unsigned long long)cfg->env.seed,
           cfg->env.grid_width,
           cfg->env.grid_height,
           cfg->env.p,
           cfg->env.f,
           cfg->env.episode_step_cap,
           cfg->smoke_step_cap);
    print_counts("step=", 0, &env);
    printf("\n");

    CrFfmStepResult last;
    memset(&last, 0, sizeof(last));
    int steps_run = 0;
    for (int i = 0; i < cfg->smoke_step_cap; i++) {
        last = cr_ffm_step_unmanaged(&env);
        steps_run = env.step_count;
        if (env.step_count % cfg->debug_every == 0 || env.step_count == 1 || env.step_count == cfg->smoke_step_cap || last.truncated) {
            print_counts("step=", env.step_count, &env);
            printf(" active_before=%d active_after=%d regrowths=%d lightning=%d truncated=%d\n",
                   last.active_before,
                   last.active_after,
                   last.regrowths,
                   last.lightning_ignitions,
                   last.truncated);
        }
        if (last.truncated) break;
    }

    printf("result=pass steps_run=%d truncated=%d empty=%d tree=%d burning=%d total_cells=%d\n",
           steps_run,
           last.truncated,
           count_state(&env, CR_FFM_EMPTY),
           count_state(&env, CR_FFM_TREE),
           count_state(&env, CR_FFM_BURNING),
           env.cell_count);
    cr_ffm_free(&env);
    return 0;
}

int main(int argc, char **argv) {
    DemoConfig cfg = demo_default_config();
    parse_args(&cfg, argc, argv);
    validate_demo_config(&cfg);
    return run_demo(&cfg);
}
