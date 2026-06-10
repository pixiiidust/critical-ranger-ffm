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

typedef struct {
    CrFfmConfig cfg;
    CrFfmRng rng;
    int cell_count;
    int step_count;
    unsigned char *grid;
} CrFfmSnapshot;

typedef struct {
    int step_count;
    int cell_count;
    double *regrowth_draws;
    double *lightning_draws;
} CrFfmReplayTape;

typedef enum {
    CR_FFM_BRANCH_INVARIANT_OK = 0,
    CR_FFM_BRANCH_INVARIANT_NULL_ENV = 1,
    CR_FFM_BRANCH_INVARIANT_CONFIG_MISMATCH = 2,
    CR_FFM_BRANCH_INVARIANT_RNG_MISMATCH = 3,
    CR_FFM_BRANCH_INVARIANT_STEP_MISMATCH = 4,
    CR_FFM_BRANCH_INVARIANT_GRID_MISMATCH = 5
} CrFfmBranchInvariantReason;

typedef struct {
    int valid;
    int mismatch_count;
    int first_mismatch;
    CrFfmBranchInvariantReason reason;
} CrFfmBranchInvariantResult;

CrFfmConfig cr_ffm_default_config(void);
int cr_ffm_validate_config(const CrFfmConfig *cfg);
int cr_ffm_init(CrFfmEnv *env, const CrFfmConfig *cfg);
void cr_ffm_free(CrFfmEnv *env);
int cr_ffm_snapshot_init(CrFfmSnapshot *snapshot, const CrFfmEnv *env);
void cr_ffm_snapshot_free(CrFfmSnapshot *snapshot);
int cr_ffm_restore(CrFfmEnv *env, const CrFfmSnapshot *snapshot);
int cr_ffm_env_matches_snapshot(const CrFfmEnv *env, const CrFfmSnapshot *snapshot);
int cr_ffm_replay_tape_init(CrFfmReplayTape *tape, const CrFfmSnapshot *snapshot, int step_count);
void cr_ffm_replay_tape_free(CrFfmReplayTape *tape);
CrFfmStepResult cr_ffm_step_unmanaged(CrFfmEnv *env);
CrFfmStepResult cr_ffm_step_unmanaged_with_burned_mask(CrFfmEnv *env, unsigned char *burned_mask);
CrFfmStepResult cr_ffm_step_unmanaged_with_replay(CrFfmEnv *env, const CrFfmReplayTape *tape, int replay_step, unsigned char *burned_mask);
CrFfmBranchInvariantResult cr_ffm_check_branch_invariant(const CrFfmEnv *treatment, const CrFfmEnv *control, int allowed_mismatch_index);
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
