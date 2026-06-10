#include "critical_ranger_ffm.h"

#define OBS_SIZE (128 * 128 * FFM_C1_OCEAN_OBS_CHANNELS)
#define NUM_ATNS 1
#define ACT_SIZES {128 * 128 + 1}
#define OBS_TENSOR_T FloatTensor

#define Env CriticalRangerFfm
#include "vecenv.h"

void my_init(Env *env, Dict *kwargs) {
    (void)kwargs;
    env->num_agents = 1;
}

void my_log(Log *log, Dict *out) {
    dict_set(out, "perf", log->perf);
    dict_set(out, "score", log->score);
    dict_set(out, "episode_return", log->episode_return);
    dict_set(out, "episode_length", log->episode_length);
    dict_set(out, "effective_interventions", log->effective_interventions);
}
