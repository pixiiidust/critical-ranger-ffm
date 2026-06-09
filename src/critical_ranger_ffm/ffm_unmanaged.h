#ifndef CRITICAL_RANGER_FFM_UNMANAGED_H
#define CRITICAL_RANGER_FFM_UNMANAGED_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define CR_FFM_EMPTY 0
#define CR_FFM_TREE 1
#define CR_FFM_BURNING 2
#define CR_FFM_CONNECTIVITY_4 4

typedef struct {
    int grid_width;
    int grid_height;
    double p;
    double f;
    uint64_t seed;
    double initial_tree_density;
    int episode_step_cap;
    int connectivity;
} CrFfmConfig;

typedef struct {
    int component_count;
    int total_burned;
    int largest_component_size;
    int sizes_written;
    int overflowed;
} CrFfmClusterSummary;

typedef struct {
    uint64_t state;
} CrFfmRng;

typedef struct {
    int active_before;
    int active_after;
    int regrowths;
    int lightning_ignitions;
    int tree_count;
    int truncated;
} CrFfmStepResult;

typedef struct {
    CrFfmConfig cfg;
    CrFfmRng rng;
    int cell_count;
    int step_count;
    unsigned char *grid;
    unsigned char *next;
} CrFfmEnv;

CrFfmConfig cr_ffm_default_config(void);
int cr_ffm_validate_config(const CrFfmConfig *cfg);
int cr_ffm_init(CrFfmEnv *env, const CrFfmConfig *cfg);
void cr_ffm_free(CrFfmEnv *env);
CrFfmStepResult cr_ffm_step_unmanaged(CrFfmEnv *env);
int cr_ffm_can_label_fire_clusters(const CrFfmEnv *env);
int cr_ffm_hk_label_burned_mask(const unsigned char *burned_mask,
                                int width,
                                int height,
                                int connectivity,
                                int *labels,
                                int *component_sizes,
                                int max_components,
                                CrFfmClusterSummary *summary);

#ifdef __cplusplus
}
#endif

#endif
