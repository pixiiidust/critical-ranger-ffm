#ifndef CRITICAL_RANGER_FFM_C1_OCEAN_PROVISIONAL_H
#define CRITICAL_RANGER_FFM_C1_OCEAN_PROVISIONAL_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define FFM_C1_EMPTY 0
#define FFM_C1_TREE 1
#define FFM_C1_BURNING 2
#define FFM_C1_OBS_CHANNELS 3

typedef struct {
    int grid_width;
    int grid_height;
    double p;
    double f;
    uint64_t seed;
    double initial_tree_density;
    int episode_step_cap;
    float dummy_reward;
} FfmC1Config;

typedef struct {
    uint64_t state;
} FfmC1Rng;

typedef struct {
    int row;
    int col;
    int is_noop;
    int is_valid;
} FfmC1DecodedAction;

typedef struct {
    float reward;
    int truncated;
    int effective_intervention;
    int lightning_ignitions;
    int active_after;
} FfmC1StepResult;

typedef struct {
    FfmC1Config cfg;
    FfmC1Rng rng;
    int cell_count;
    int action_count;
    int obs_count;
    int step_count;
    unsigned char *grid;
    unsigned char *next;
    float *obs;
} FfmC1Env;

FfmC1Config ffm_c1_default_config(void);
int ffm_c1_validate_config(const FfmC1Config *cfg);
int ffm_c1_init(FfmC1Env *env, const FfmC1Config *cfg);
void ffm_c1_free(FfmC1Env *env);
FfmC1DecodedAction ffm_c1_decode_action(int action, int grid_width, int grid_height);
int ffm_c1_random_action(FfmC1Rng *rng, int action_count);
void ffm_c1_write_observation(FfmC1Env *env);
FfmC1StepResult ffm_c1_step(FfmC1Env *env, int action);
int ffm_c1_run_self_tests(void);
int ffm_c1_run_random_demo(const FfmC1Config *cfg, int steps);

#ifdef __cplusplus
}
#endif

#endif
