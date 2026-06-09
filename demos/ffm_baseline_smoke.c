// Critical Ranger FFM Part C0: unmanaged baseline smoke-test demo.
// CPU-only standalone C. No agent, no reward, no Puffer/Ocean training.

#include <errno.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#define EMPTY 0
#define TREE 1
#define BURNING 2
#define MAX_LINE 512

// Keep this order byte-for-byte compatible with Part B REQUIRED_CLUSTER_COLUMNS.
static const char *CSV_HEADER =
    "schema_version,run_id,mode,seed,episode_id,step,event_id,cluster_id,fire_size,"
    "grid_width,grid_height,p,f,global_tree_density,quiet_window_component_count,overlap_signal,pair_id,source,notes\n";

typedef struct {
    int grid_width;
    int grid_height;
    int min_gate_grid_size;
    double p;
    double f;
    uint64_t seed;
    double initial_tree_density;
    int warmup_steps;
    int cluster_target;
    int max_steps;
    int connectivity;
    int schema_version;
    char run_id[128];
    char out[256];
    char summary[256];
    double min_orders_of_magnitude;
    double overlap_warn_rate;
} Config;

typedef struct {
    uint64_t state;
} Rng;

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
} RowVec;

typedef struct {
    int cluster_count;
    int fire_size_min;
    int fire_size_max;
    int tail_count;
    int multi_component_windows;
    int closed_windows;
    int overlap_ignition_steps;
    int steps_run;
    int stopped_by_cluster_target;
    double density_mean;
    double density_m2;
    int density_samples;
} Stats;

static void die(const char *msg) {
    fprintf(stderr, "ERROR: %s\n", msg);
    exit(1);
}

static void *xcalloc(size_t n, size_t size) {
    void *ptr = calloc(n, size);
    if (!ptr) die("allocation failed");
    return ptr;
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

static uint64_t rng_next_u64(Rng *rng) {
    // SplitMix64: deterministic, portable enough for smoke/replay checks.
    uint64_t z = (rng->state += 0x9E3779B97F4A7C15ULL);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}

static double rng_unit(Rng *rng) {
    return (rng_next_u64(rng) >> 11) * (1.0 / 9007199254740992.0);
}

static Config default_config(void) {
    Config cfg;
    cfg.grid_width = 128;
    cfg.grid_height = 128;
    cfg.min_gate_grid_size = 128;
    cfg.p = 0.01;
    cfg.f = 0.000001;
    cfg.seed = 20260609ULL;
    cfg.initial_tree_density = 0.55;
    cfg.warmup_steps = 10000;
    cfg.cluster_target = 300;
    cfg.max_steps = 200000;
    cfg.connectivity = 4;
    cfg.schema_version = 1;
    snprintf(cfg.run_id, sizeof(cfg.run_id), "part-c0-baseline-smoke");
    snprintf(cfg.out, sizeof(cfg.out), "data/fixtures/part_c0_baseline_clusters.csv");
    snprintf(cfg.summary, sizeof(cfg.summary), "reports/part-c0-baseline-smoke/summary.json");
    cfg.min_orders_of_magnitude = 1.5;
    cfg.overlap_warn_rate = 0.10;
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

static void set_config(Config *cfg, const char *key, const char *value) {
    if (strcmp(key, "grid_width") == 0) cfg->grid_width = atoi(value);
    else if (strcmp(key, "grid_height") == 0) cfg->grid_height = atoi(value);
    else if (strcmp(key, "min_gate_grid_size") == 0) cfg->min_gate_grid_size = atoi(value);
    else if (strcmp(key, "p") == 0) cfg->p = atof(value);
    else if (strcmp(key, "f") == 0) cfg->f = atof(value);
    else if (strcmp(key, "seed") == 0) cfg->seed = strtoull(value, NULL, 10);
    else if (strcmp(key, "initial_tree_density") == 0) cfg->initial_tree_density = atof(value);
    else if (strcmp(key, "warmup_steps") == 0) cfg->warmup_steps = atoi(value);
    else if (strcmp(key, "cluster_target") == 0) cfg->cluster_target = atoi(value);
    else if (strcmp(key, "max_steps") == 0) cfg->max_steps = atoi(value);
    else if (strcmp(key, "connectivity") == 0) cfg->connectivity = atoi(value);
    else if (strcmp(key, "schema_version") == 0) cfg->schema_version = atoi(value);
    else if (strcmp(key, "run_id") == 0) snprintf(cfg->run_id, sizeof(cfg->run_id), "%s", value);
    else if (strcmp(key, "out") == 0) snprintf(cfg->out, sizeof(cfg->out), "%s", value);
    else if (strcmp(key, "summary") == 0) snprintf(cfg->summary, sizeof(cfg->summary), "%s", value);
    else if (strcmp(key, "min_orders_of_magnitude") == 0) cfg->min_orders_of_magnitude = atof(value);
    else if (strcmp(key, "overlap_warn_rate") == 0) cfg->overlap_warn_rate = atof(value);
}

static void load_config_file(Config *cfg, const char *path) {
    FILE *fp = fopen(path, "r");
    if (!fp) die("could not open config file");
    char line[MAX_LINE];
    while (fgets(line, sizeof(line), fp)) {
        trim(line);
        if (line[0] == '\0' || line[0] == '#') continue;
        char *eq = strchr(line, '=');
        if (!eq) continue;
        *eq = '\0';
        char *key = line;
        char *value = eq + 1;
        trim(key);
        trim(value);
        set_config(cfg, key, value);
    }
    fclose(fp);
}

static void parse_args(Config *cfg, int argc, char **argv, int *self_test) {
    *self_test = 0;
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--self-test") == 0) {
            *self_test = 1;
        } else if (strcmp(argv[i], "--config") == 0 && i + 1 < argc) {
            load_config_file(cfg, argv[++i]);
        } else if (strncmp(argv[i], "--", 2) == 0 && i + 1 < argc) {
            char key[128];
            snprintf(key, sizeof(key), "%s", argv[i] + 2);
            for (char *p = key; *p; p++) if (*p == '-') *p = '_';
            set_config(cfg, key, argv[++i]);
        } else {
            die("unknown or incomplete argument");
        }
    }
}

static void validate_config(const Config *cfg) {
    if (cfg->grid_width <= 0 || cfg->grid_height <= 0) die("grid size must be positive");
    if (cfg->connectivity != 4) die("Part C0 requires connectivity=4");
    if (cfg->p < 0.0 || cfg->p > 1.0 || cfg->f < 0.0 || cfg->f > 1.0) die("p and f must be probabilities");
    if (cfg->warmup_steps < 0 || cfg->cluster_target <= 0 || cfg->max_steps <= 0) die("warmup/target/max steps invalid");
}

static int idx(int row, int col, int width) { return row * width + col; }

static int has_burning_neighbor(const unsigned char *grid, int r, int c, int w, int h) {
    if (r > 0 && grid[idx(r - 1, c, w)] == BURNING) return 1;
    if (r + 1 < h && grid[idx(r + 1, c, w)] == BURNING) return 1;
    if (c > 0 && grid[idx(r, c - 1, w)] == BURNING) return 1;
    if (c + 1 < w && grid[idx(r, c + 1, w)] == BURNING) return 1;
    return 0;
}

static int count_state(const unsigned char *grid, int n, unsigned char state) {
    int count = 0;
    for (int i = 0; i < n; i++) if (grid[i] == state) count++;
    return count;
}

static void init_grid(unsigned char *grid, int n, double density, Rng *rng) {
    for (int i = 0; i < n; i++) grid[i] = rng_unit(rng) < density ? TREE : EMPTY;
}

static void rows_push(RowVec *rows, ClusterRow row) {
    if (rows->count == rows->capacity) {
        int next = rows->capacity == 0 ? 256 : rows->capacity * 2;
        ClusterRow *items = (ClusterRow *)realloc(rows->items, (size_t)next * sizeof(ClusterRow));
        if (!items) die("row realloc failed");
        rows->items = items;
        rows->capacity = next;
    }
    rows->items[rows->count++] = row;
}

static int uf_find(int *parent, int x) {
    while (parent[x] != x) {
        parent[x] = parent[parent[x]];
        x = parent[x];
    }
    return x;
}

static void uf_union(int *parent, int a, int b) {
    int ra = uf_find(parent, a);
    int rb = uf_find(parent, b);
    if (ra != rb) parent[rb] = ra;
}

static int hk_label_mask(const unsigned char *mask, int w, int h, int *sizes, int max_sizes) {
    int n = w * h;
    int *labels = (int *)xcalloc((size_t)n, sizeof(int));
    int *parent = (int *)xcalloc((size_t)n + 1, sizeof(int));
    int next_label = 1;

    for (int r = 0; r < h; r++) {
        for (int c = 0; c < w; c++) {
            int at = idx(r, c, w);
            if (!mask[at]) continue;
            int left = c > 0 ? labels[idx(r, c - 1, w)] : 0;
            int up = r > 0 ? labels[idx(r - 1, c, w)] : 0;
            if (!left && !up) {
                labels[at] = next_label;
                parent[next_label] = next_label;
                next_label++;
            } else if (left && !up) {
                labels[at] = left;
            } else if (!left && up) {
                labels[at] = up;
            } else {
                labels[at] = left;
                uf_union(parent, left, up);
            }
        }
    }

    int *root_to_slot = (int *)xcalloc((size_t)next_label + 1, sizeof(int));
    int components = 0;
    for (int i = 0; i < n; i++) {
        if (!labels[i]) continue;
        int root = uf_find(parent, labels[i]);
        int slot = root_to_slot[root];
        if (!slot) {
            components++;
            if (components <= max_sizes) sizes[components - 1] = 0;
            root_to_slot[root] = components;
            slot = components;
        }
        if (slot <= max_sizes) sizes[slot - 1]++;
    }

    free(root_to_slot);
    free(parent);
    free(labels);
    return components;
}

static int step_physics(unsigned char *grid, unsigned char *next, unsigned char *burned_mask, int w, int h, const Config *cfg, Rng *rng, int *lightning_ignitions) {
    int n = w * h;
    *lightning_ignitions = 0;

    for (int i = 0; i < n; i++) {
        if (grid[i] == EMPTY && rng_unit(rng) < cfg->p) grid[i] = TREE;
        if (grid[i] == TREE && rng_unit(rng) < cfg->f) {
            grid[i] = BURNING;
            (*lightning_ignitions)++;
        }
    }

    int active_after = 0;
    for (int r = 0; r < h; r++) {
        for (int c = 0; c < w; c++) {
            int at = idx(r, c, w);
            unsigned char state = grid[at];
            if (state == BURNING) {
                burned_mask[at] = 1;
                next[at] = EMPTY;
            } else if (state == TREE && has_burning_neighbor(grid, r, c, w, h)) {
                next[at] = BURNING;
                active_after++;
            } else {
                next[at] = state;
            }
        }
    }
    memcpy(grid, next, (size_t)n);
    return active_after;
}

static void update_density_stats(Stats *stats, double density) {
    stats->density_samples++;
    double delta = density - stats->density_mean;
    stats->density_mean += delta / stats->density_samples;
    double delta2 = density - stats->density_mean;
    stats->density_m2 += delta * delta2;
}

static void close_event(RowVec *rows, Stats *stats, const unsigned char *burned_mask, int w, int h, int step, int event_id, double density) {
    int max_components = w * h;
    int *sizes = (int *)xcalloc((size_t)max_components, sizeof(int));
    int components = hk_label_mask(burned_mask, w, h, sizes, max_components);
    if (components > 0) {
        stats->closed_windows++;
        if (components > 1) stats->multi_component_windows++;
    }
    for (int i = 0; i < components; i++) {
        if (sizes[i] <= 0) continue;
        ClusterRow row;
        row.step = step;
        row.event_id = event_id;
        row.cluster_id = i + 1;
        row.fire_size = sizes[i];
        row.component_count = components;
        row.density = density;
        rows_push(rows, row);
        stats->cluster_count++;
        if (stats->fire_size_min == 0 || sizes[i] < stats->fire_size_min) stats->fire_size_min = sizes[i];
        if (sizes[i] > stats->fire_size_max) stats->fire_size_max = sizes[i];
    }
    free(sizes);
}

static double orders_of_magnitude_int(int lo, int hi) {
    if (lo <= 0 || hi <= 0 || hi < lo) return 0.0;
    return log10((double)hi / (double)lo);
}

static void write_csv(const Config *cfg, const RowVec *rows) {
    ensure_parent_dir(cfg->out);
    FILE *fp = fopen(cfg->out, "w");
    if (!fp) die("could not write cluster csv");
    fputs(CSV_HEADER, fp);
    for (int i = 0; i < rows->count; i++) {
        const ClusterRow *r = &rows->items[i];
        fprintf(fp,
            "%d,%s,baseline,%llu,0,%d,%d,%d,%d,%d,%d,%.10g,%.10g,%.8f,%d,%s,,env,part-c0-unmanaged-baseline\n",
            cfg->schema_version,
            cfg->run_id,
            (unsigned long long)cfg->seed,
            r->step,
            r->event_id,
            r->cluster_id,
            r->fire_size,
            cfg->grid_width,
            cfg->grid_height,
            cfg->p,
            cfg->f,
            r->density,
            r->component_count,
            r->component_count > 1 ? "multi_component" : "single_component");
    }
    fclose(fp);
}

static const char *pass_warn(int ok) { return ok ? "pass" : "warn"; }

static void write_summary(const Config *cfg, const Stats *stats) {
    ensure_parent_dir(cfg->summary);
    FILE *fp = fopen(cfg->summary, "w");
    if (!fp) die("could not write summary json");
    double density_var = stats->density_samples > 1 ? stats->density_m2 / (stats->density_samples - 1) : 0.0;
    double density_sd = density_var > 0.0 ? sqrt(density_var) : 0.0;
    double density_min = stats->density_mean - density_sd;
    double density_max = stats->density_mean + density_sd;
    double orders = orders_of_magnitude_int(stats->fire_size_min, stats->fire_size_max);
    double overlap_rate = stats->closed_windows > 0 ? (double)stats->multi_component_windows / stats->closed_windows : 0.0;
    int measurement_ok = cfg->grid_width >= cfg->min_gate_grid_size && cfg->grid_height >= cfg->min_gate_grid_size;
    int sample_ok = stats->cluster_count >= cfg->cluster_target;
    int range_ok = orders >= cfg->min_orders_of_magnitude;
    int overlap_ok = overlap_rate <= cfg->overlap_warn_rate;
    int density_ok = stats->density_samples > 0;
    int heavy_tail_ok = sample_ok && range_ok && stats->fire_size_max >= 10;

    fprintf(fp, "{\n");
    fprintf(fp, "  \"run_id\": \"%s\",\n", cfg->run_id);
    fprintf(fp, "  \"grid_width\": %d,\n", cfg->grid_width);
    fprintf(fp, "  \"grid_height\": %d,\n", cfg->grid_height);
    fprintf(fp, "  \"min_gate_grid_size\": %d,\n", cfg->min_gate_grid_size);
    fprintf(fp, "  \"p\": %.10g,\n", cfg->p);
    fprintf(fp, "  \"f\": %.10g,\n", cfg->f);
    fprintf(fp, "  \"f_over_p\": %.10g,\n", cfg->p > 0.0 ? cfg->f / cfg->p : 0.0);
    fprintf(fp, "  \"seed\": %llu,\n", (unsigned long long)cfg->seed);
    fprintf(fp, "  \"warmup_steps_used\": %d,\n", cfg->warmup_steps);
    fprintf(fp, "  \"density_samples_after_warmup\": %d,\n", stats->density_samples);
    fprintf(fp, "  \"critical_density_mean\": %.8f,\n", stats->density_mean);
    fprintf(fp, "  \"critical_density_band_min\": %.8f,\n", density_min);
    fprintf(fp, "  \"critical_density_band_max\": %.8f,\n", density_max);
    fprintf(fp, "  \"steps_run\": %d,\n", stats->steps_run);
    fprintf(fp, "  \"stopped_by_cluster_target\": %s,\n", stats->stopped_by_cluster_target ? "true" : "false");
    fprintf(fp, "  \"cluster_target\": %d,\n", cfg->cluster_target);
    fprintf(fp, "  \"cluster_count\": %d,\n", stats->cluster_count);
    fprintf(fp, "  \"fire_size_min\": %d,\n", stats->fire_size_min);
    fprintf(fp, "  \"fire_size_max\": %d,\n", stats->fire_size_max);
    fprintf(fp, "  \"orders_of_magnitude\": %.6f,\n", orders);
    fprintf(fp, "  \"closed_windows\": %d,\n", stats->closed_windows);
    fprintf(fp, "  \"multi_component_windows\": %d,\n", stats->multi_component_windows);
    fprintf(fp, "  \"multi_component_window_rate\": %.6f,\n", overlap_rate);
    fprintf(fp, "  \"overlap_ignition_steps\": %d,\n", stats->overlap_ignition_steps);
    fprintf(fp, "  \"measurement_grid_gate\": \"%s\",\n", pass_warn(measurement_ok));
    fprintf(fp, "  \"sample_size_gate\": \"%s\",\n", pass_warn(sample_ok));
    fprintf(fp, "  \"size_range_gate\": \"%s\",\n", pass_warn(range_ok));
    fprintf(fp, "  \"overlap_gate\": \"%s\",\n", pass_warn(overlap_ok));
    fprintf(fp, "  \"critical_density_gate\": \"%s\",\n", pass_warn(density_ok));
    fprintf(fp, "  \"heavy_tail_gate\": \"%s\"\n", pass_warn(heavy_tail_ok));
    fprintf(fp, "}\n");
    fclose(fp);

    printf("Part C0 unmanaged baseline smoke summary\n");
    printf("grid=%dx%d min_gate=%d measurement_grid=%s\n", cfg->grid_width, cfg->grid_height, cfg->min_gate_grid_size, pass_warn(measurement_ok));
    printf("p=%.10g f=%.10g f/p=%.10g seed=%llu\n", cfg->p, cfg->f, cfg->p > 0.0 ? cfg->f / cfg->p : 0.0, (unsigned long long)cfg->seed);
    printf("warmup_steps_used=%d density_samples_after_warmup=%d critical_density_mean=%.6f band=[%.6f, %.6f]\n",
           cfg->warmup_steps, stats->density_samples, stats->density_mean, density_min, density_max);
    printf("steps_run=%d clusters=%d fire_size_range=%d..%d orders=%.3f\n",
           stats->steps_run, stats->cluster_count, stats->fire_size_min, stats->fire_size_max, orders);
    printf("closed_windows=%d multi_component_windows=%d multi_component_rate=%.3f overlap_ignition_steps=%d\n",
           stats->closed_windows, stats->multi_component_windows, overlap_rate, stats->overlap_ignition_steps);
    printf("gates: sample=%s heavy_tail=%s size_range=%s overlap=%s critical_density=%s\n",
           pass_warn(sample_ok), pass_warn(heavy_tail_ok), pass_warn(range_ok), pass_warn(overlap_ok), pass_warn(density_ok));
    printf("csv=%s\nsummary=%s\n", cfg->out, cfg->summary);
}

static int run_simulation(const Config *cfg) {
    validate_config(cfg);
    int w = cfg->grid_width;
    int h = cfg->grid_height;
    int n = w * h;
    Rng rng = { cfg->seed };
    unsigned char *grid = (unsigned char *)xcalloc((size_t)n, sizeof(unsigned char));
    unsigned char *next = (unsigned char *)xcalloc((size_t)n, sizeof(unsigned char));
    unsigned char *burned_mask = (unsigned char *)xcalloc((size_t)n, sizeof(unsigned char));
    init_grid(grid, n, cfg->initial_tree_density, &rng);

    RowVec rows = {0};
    Stats stats;
    memset(&stats, 0, sizeof(stats));
    int event_active = 0;
    int event_id = 0;

    for (int step = 1; step <= cfg->max_steps; step++) {
        int active_before = count_state(grid, n, BURNING);
        int tree_before = count_state(grid, n, TREE);
        int lightning_ignitions = 0;
        int active_after = step_physics(grid, next, burned_mask, w, h, cfg, &rng, &lightning_ignitions);
        if (active_before > 0 && lightning_ignitions > 0) stats.overlap_ignition_steps++;
        if (!event_active && (active_before > 0 || lightning_ignitions > 0 || active_after > 0)) {
            event_active = 1;
            event_id++;
        }
        double density = (double)count_state(grid, n, TREE) / (double)n;
        if (step > cfg->warmup_steps) update_density_stats(&stats, density);
        (void)tree_before;

        if (step <= cfg->warmup_steps) {
            // Warm-up is discarded for both density estimation and cluster logging.
            // This keeps the baseline gates from measuring the initial transient.
            memset(burned_mask, 0, (size_t)n);
            event_active = 0;
            event_id = 0;
            stats.steps_run = step;
            continue;
        }

        if (event_active && active_after == 0) {
            close_event(&rows, &stats, burned_mask, w, h, step, event_id, density);
            memset(burned_mask, 0, (size_t)n);
            event_active = 0;
            if (stats.cluster_count >= cfg->cluster_target) {
                stats.steps_run = step;
                stats.stopped_by_cluster_target = 1;
                break;
            }
        }
        stats.steps_run = step;
    }

    write_csv(cfg, &rows);
    write_summary(cfg, &stats);
    free(rows.items);
    free(burned_mask);
    free(next);
    free(grid);
    return 0;
}

static int assert_true(int condition, const char *name) {
    if (!condition) {
        fprintf(stderr, "self-test failed: %s\n", name);
        return 0;
    }
    return 1;
}

static int run_self_tests(void) {
    int ok = 1;
    unsigned char grid[9] = {TREE, TREE, TREE, TREE, BURNING, TREE, TREE, TREE, TREE};
    unsigned char next[9] = {0};
    unsigned char mask[9] = {0};
    Config cfg = default_config();
    cfg.p = 0.0;
    cfg.f = 0.0;
    Rng rng = {1};
    int lightning = 0;
    int active = step_physics(grid, next, mask, 3, 3, &cfg, &rng, &lightning);
    ok &= assert_true(active == 4, "snapshot spread ignites exactly orthogonal neighbors");
    ok &= assert_true(grid[4] == EMPTY, "snapshot burning cell burns out");
    ok &= assert_true(grid[0] == TREE && grid[2] == TREE && grid[6] == TREE && grid[8] == TREE, "no in-place cascade to diagonals/corners");
    ok &= assert_true(grid[1] == BURNING && grid[3] == BURNING && grid[5] == BURNING && grid[7] == BURNING, "orthogonal neighbors become burning");

    unsigned char known_mask[16] = {
        1, 1, 0, 1,
        0, 1, 0, 1,
        0, 0, 0, 0,
        1, 0, 1, 1,
    };
    int sizes[16] = {0};
    int comps = hk_label_mask(known_mask, 4, 4, sizes, 16);
    ok &= assert_true(comps == 4, "HK known mask component count");
    int saw3 = 0, saw2 = 0, saw1 = 0;
    for (int i = 0; i < comps; i++) {
        if (sizes[i] == 3) saw3++;
        if (sizes[i] == 2) saw2++;
        if (sizes[i] == 1) saw1++;
    }
    ok &= assert_true(saw3 == 1 && saw2 == 2 && saw1 == 1, "HK known mask component sizes");

    if (ok) {
        printf("self-test: PASS\n");
        return 0;
    }
    return 1;
}

int main(int argc, char **argv) {
    Config cfg = default_config();
    int self_test = 0;
    parse_args(&cfg, argc, argv, &self_test);
    if (self_test) return run_self_tests();
    return run_simulation(&cfg);
}
