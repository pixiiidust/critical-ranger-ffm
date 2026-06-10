#ifndef CRITICAL_RANGER_FFM_C1_OCEAN_BINDING_H
#define CRITICAL_RANGER_FFM_C1_OCEAN_BINDING_H

#include "../ffm_unmanaged.h"

#ifdef __cplusplus
extern "C" {
#endif

#define FFM_C1_OCEAN_OBS_CHANNELS 3

typedef struct {
    CrFfmConfig ffm;
    float gamma;
} FfmC1OceanConfig;

typedef struct {
    int row;
    int col;
    int is_noop;
    int is_valid;
} FfmC1OceanDecodedAction;

typedef struct {
    float reward;
    int truncated;
    int effective_intervention;
    CrFfmStepResult ffm;
} FfmC1OceanStepResult;

typedef struct {
    CrFfmEnv ffm;
    int action_count;
    int obs_count;
    float *obs;
} FfmC1OceanEnv;

FfmC1OceanConfig ffm_c1_ocean_default_config(void);
int ffm_c1_ocean_validate_config(const FfmC1OceanConfig *cfg);
int ffm_c1_ocean_init(FfmC1OceanEnv *env, const FfmC1OceanConfig *cfg);
void ffm_c1_ocean_free(FfmC1OceanEnv *env);
FfmC1OceanDecodedAction ffm_c1_ocean_decode_action(int action, int grid_width, int grid_height);
void ffm_c1_ocean_write_observation(FfmC1OceanEnv *env);
FfmC1OceanStepResult ffm_c1_ocean_step(FfmC1OceanEnv *env, int action);

#ifdef __cplusplus
}
#endif

#endif
