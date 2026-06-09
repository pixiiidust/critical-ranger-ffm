// Critical Ranger FFM unmanaged demo smoke.
// CPU-only standalone path around the real unmanaged C seam. No Puffer, GPU, train, or eval.

#include "ffm_unmanaged.h"

#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#define MAX_LINE 512

typedef struct {
    CrFfmConfig env;
    int smoke_step_cap;
    int debug_every;
    char run_id[128];
    char clusters_csv[256];
    char summary_json[256];
} DemoConfig;

typedef struct {
    int step;
    int event_id;
    int cluster_id;
    int fire_size;
    int component_count;
    double density;
} ClusterRow;

typedef struct {
    ClusterRow *items;
    int count;
    int capacity;
} ClusterRows;

typedef struct {
    int steps_run;
    int closed_window_count;
    int closed_cluster_count;
    int cluster_size_min;
    int cluster_size_max;
    int overlap_warning_count;
} SmokeStats;

static const char *CSV_HEADER =
    "schema_version,run_id,mode,seed,episode_id,step,event_id,cluster_id,fire_size,"
    "grid_width,grid_height,p,f,global_tree_density,quiet_window_component_count,"
    "overlap_signal,pair_id,source,notes\n";

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
    snprintf(cfg.run_id, sizeof(cfg.run_id), "unmanaged-demo-smoke");
    cfg.clusters_csv[0] = '\0';
    cfg.summary_json[0] = '\0';
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
    } else if (strcmp(key, "run_id") == 0) {
        snprintf(cfg->run_id, sizeof(cfg->run_id), "%s", value);
    } else if (strcmp(key, "clusters_csv") == 0) {
        snprintf(cfg->clusters_csv, sizeof(cfg->clusters_csv), "%s", value);
    } else if (strcmp(key, "summary_json") == 0) {
        snprintf(cfg->summary_json, sizeof(cfg->summary_json), "%s", value);
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

static void ensure_parent_dir(const char *path) {
    const char *slash = strrchr(path, '/');
    if (!slash) return;
    size_t len = (size_t)(slash - path);
    if (len == 0 || len >= 512) return;
    char dir[512];
    memcpy(dir, path, len);
    dir[len] = '\0';
    for (char *p = dir + 1; *p; p++) {
        if (*p == '/') {
            *p = '\0';
            if (mkdir(dir, 0775) != 0 && errno != EEXIST) die("failed to create output directory");
            *p = '/';
        }
    }
    if (mkdir(dir, 0775) != 0 && errno != EEXIST) die("failed to create output directory");
}

static void rows_push(ClusterRows *rows, ClusterRow row) {
    if (rows->count == rows->capacity) {
        int next_capacity = rows->capacity == 0 ? 32 : rows->capacity * 2;
        ClusterRow *next = (ClusterRow *)realloc(rows->items, (size_t)next_capacity * sizeof(ClusterRow));
        if (!next) die("row allocation failed");
        rows->items = next;
        rows->capacity = next_capacity;
    }
    rows->items[rows->count++] = row;
}

static void merge_masks(unsigned char *event_mask, const unsigned char *step_mask, int n) {
    for (int i = 0; i < n; i++) {
        if (step_mask[i]) event_mask[i] = 1;
    }
}

static void close_event(const DemoConfig *cfg, const CrFfmEnv *env, ClusterRows *rows, SmokeStats *stats, const unsigned char *event_mask, int event_id, double density) {
    int max_components = env->cell_count;
    int *labels = (int *)calloc((size_t)env->cell_count, sizeof(int));
    int *sizes = (int *)calloc((size_t)max_components, sizeof(int));
    CrFfmClusterSummary summary;
    if (!labels || !sizes) die("cluster allocation failed");
    if (!cr_ffm_hk_label_burned_mask(event_mask, cfg->env.grid_width, cfg->env.grid_height, cfg->env.connectivity, labels, sizes, max_components, &summary)) {
        die("failed to label quiet-window clusters");
    }
    if (summary.component_count > 0) {
        stats->closed_window_count++;
        if (summary.component_count > 1) stats->overlap_warning_count++;
    }
    for (int i = 0; i < summary.sizes_written; i++) {
        if (sizes[i] <= 0) continue;
        ClusterRow row;
        row.step = env->step_count;
        row.event_id = event_id;
        row.cluster_id = i + 1;
        row.fire_size = sizes[i];
        row.component_count = summary.component_count;
        row.density = density;
        rows_push(rows, row);
        stats->closed_cluster_count++;
        if (stats->cluster_size_min == 0 || sizes[i] < stats->cluster_size_min) stats->cluster_size_min = sizes[i];
        if (sizes[i] > stats->cluster_size_max) stats->cluster_size_max = sizes[i];
    }
    free(sizes);
    free(labels);
}

static void write_cluster_csv(const DemoConfig *cfg, const ClusterRows *rows) {
    if (cfg->clusters_csv[0] == '\0') return;
    ensure_parent_dir(cfg->clusters_csv);
    FILE *fp = fopen(cfg->clusters_csv, "w");
    if (!fp) die("could not write unmanaged demo cluster csv");
    fputs(CSV_HEADER, fp);
    for (int i = 0; i < rows->count; i++) {
        const ClusterRow *row = &rows->items[i];
        const char *overlap = row->component_count > 1 ? "multi_component" : "single_component";
        fprintf(fp,
                "1,%s,baseline,%llu,0,%d,%d,%d,%d,%d,%d,%.10g,%.10g,%.8f,%d,%s,,unmanaged_demo,issue-12-unmanaged-smoke\n",
                cfg->run_id,
                (unsigned long long)cfg->env.seed,
                row->step,
                row->event_id,
                row->cluster_id,
                row->fire_size,
                cfg->env.grid_width,
                cfg->env.grid_height,
                cfg->env.p,
                cfg->env.f,
                row->density,
                row->component_count,
                overlap);
    }
    fclose(fp);
}

static void write_summary_json(const DemoConfig *cfg, const SmokeStats *stats) {
    if (cfg->summary_json[0] == '\0') return;
    ensure_parent_dir(cfg->summary_json);
    FILE *fp = fopen(cfg->summary_json, "w");
    if (!fp) die("could not write unmanaged demo summary json");
    double overlap_rate = stats->closed_window_count > 0 ? (double)stats->overlap_warning_count / (double)stats->closed_window_count : 0.0;
    fprintf(fp, "{\n");
    fprintf(fp, "  \"run_id\": \"%s\",\n", cfg->run_id);
    fprintf(fp, "  \"seed\": %llu,\n", (unsigned long long)cfg->env.seed);
    fprintf(fp, "  \"grid_width\": %d,\n", cfg->env.grid_width);
    fprintf(fp, "  \"grid_height\": %d,\n", cfg->env.grid_height);
    fprintf(fp, "  \"p\": %.10g,\n", cfg->env.p);
    fprintf(fp, "  \"f\": %.10g,\n", cfg->env.f);
    fprintf(fp, "  \"initial_tree_density\": %.10g,\n", cfg->env.initial_tree_density);
    fprintf(fp, "  \"episode_step_cap\": %d,\n", cfg->env.episode_step_cap);
    fprintf(fp, "  \"smoke_step_cap\": %d,\n", cfg->smoke_step_cap);
    fprintf(fp, "  \"steps_run\": %d,\n", stats->steps_run);
    fprintf(fp, "  \"closed_window_count\": %d,\n", stats->closed_window_count);
    fprintf(fp, "  \"closed_cluster_count\": %d,\n", stats->closed_cluster_count);
    fprintf(fp, "  \"cluster_size_min\": %d,\n", stats->cluster_size_min);
    fprintf(fp, "  \"cluster_size_max\": %d,\n", stats->cluster_size_max);
    fprintf(fp, "  \"overlap_rate\": %.6f,\n", overlap_rate);
    fprintf(fp, "  \"overlap_warnings\": %d\n", stats->overlap_warning_count);
    fprintf(fp, "}\n");
    fclose(fp);
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
    ClusterRows rows;
    memset(&rows, 0, sizeof(rows));
    SmokeStats stats;
    memset(&stats, 0, sizeof(stats));
    unsigned char *step_mask = (unsigned char *)calloc((size_t)env.cell_count, sizeof(unsigned char));
    unsigned char *event_mask = (unsigned char *)calloc((size_t)env.cell_count, sizeof(unsigned char));
    if (!step_mask || !event_mask) die("burn mask allocation failed");
    int steps_run = 0;
    int event_active = 0;
    int event_id = 0;
    for (int i = 0; i < cfg->smoke_step_cap; i++) {
        last = cr_ffm_step_unmanaged_with_burned_mask(&env, step_mask);
        steps_run = env.step_count;
        stats.steps_run = steps_run;
        if (last.active_before > 0 || last.lightning_ignitions > 0 || last.active_after > 0) {
            if (!event_active) {
                event_active = 1;
                event_id++;
            }
            merge_masks(event_mask, step_mask, env.cell_count);
        }
        if (env.step_count % cfg->debug_every == 0 || env.step_count == 1 || env.step_count == cfg->smoke_step_cap || last.truncated) {
            print_counts("step=", env.step_count, &env);
            printf(" active_before=%d active_after=%d regrowths=%d lightning=%d truncated=%d\n",
                   last.active_before,
                   last.active_after,
                   last.regrowths,
                   last.lightning_ignitions,
                   last.truncated);
        }
        if (event_active && last.active_after == 0) {
            double density = env.cell_count > 0 ? (double)last.tree_count / (double)env.cell_count : 0.0;
            close_event(cfg, &env, &rows, &stats, event_mask, event_id, density);
            memset(event_mask, 0, (size_t)env.cell_count * sizeof(unsigned char));
            event_active = 0;
        }
        if (last.truncated) break;
    }

    write_cluster_csv(cfg, &rows);
    write_summary_json(cfg, &stats);

    printf("result=pass steps_run=%d truncated=%d empty=%d tree=%d burning=%d total_cells=%d closed_clusters=%d overlap_warnings=%d\n",
           steps_run,
           last.truncated,
           count_state(&env, CR_FFM_EMPTY),
           count_state(&env, CR_FFM_TREE),
           count_state(&env, CR_FFM_BURNING),
           env.cell_count,
           stats.closed_cluster_count,
           stats.overlap_warning_count);
    if (cfg->clusters_csv[0] != '\0') printf("clusters_csv=%s\n", cfg->clusters_csv);
    if (cfg->summary_json[0] != '\0') printf("summary_json=%s\n", cfg->summary_json);
    free(event_mask);
    free(step_mask);
    free(rows.items);
    cr_ffm_free(&env);
    return 0;
}

int main(int argc, char **argv) {
    DemoConfig cfg = demo_default_config();
    parse_args(&cfg, argc, argv);
    validate_demo_config(&cfg);
    return run_demo(&cfg);
}
