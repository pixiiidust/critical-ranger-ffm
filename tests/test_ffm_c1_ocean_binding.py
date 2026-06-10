import subprocess
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
BINDING_SOURCE = REPO / "src" / "critical_ranger_ffm" / "ocean" / "ffm_c1_ocean_binding.c"
BINDING_HEADER = REPO / "src" / "critical_ranger_ffm" / "ocean" / "ffm_c1_ocean_binding.h"
UNMANAGED_SOURCE = REPO / "src" / "critical_ranger_ffm" / "ffm_unmanaged.c"
PUFFER_CONFIG = REPO / "pufferlib" / "config" / "critical_ranger_ffm.ini"
PUFFER_ENV = REPO / "pufferlib" / "ocean" / "critical_ranger_ffm" / "critical_ranger_ffm.c"
PUFFER_ENV_HEADER = REPO / "pufferlib" / "ocean" / "critical_ranger_ffm" / "critical_ranger_ffm.h"
PUFFER_BINDING = REPO / "pufferlib" / "ocean" / "critical_ranger_ffm" / "binding.c"
BUILD_DOC = REPO / "docs" / "references" / "pufferlib-c1-real-binding-build.md"
RENDER_PROOF_DOC = REPO / "docs" / "references" / "pufferlib-eval-render-proof.md"


class FfmC1OceanBindingTests(unittest.TestCase):
    def compile_and_run_harness(self, harness_source: str) -> str:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            harness = tmp / "harness.c"
            binary = tmp / "harness"
            harness.write_text(harness_source, encoding="utf-8")
            completed = subprocess.run(
                [
                    "cc",
                    "-std=c11",
                    "-O2",
                    "-Wall",
                    "-Wextra",
                    "-pedantic",
                    "-I",
                    str(REPO / "src"),
                    "-I",
                    str(REPO / "pufferlib" / "ocean" / "critical_ranger_ffm"),
                    "-I",
                    str(REPO / "src" / "critical_ranger_ffm" / "ocean"),
                    str(harness),
                    str(BINDING_SOURCE),
                    str(UNMANAGED_SOURCE),
                    "-o",
                    str(binary),
                ],
                cwd=REPO,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            run = subprocess.run(
                [str(binary)],
                cwd=REPO,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(run.returncode, 0, run.stderr + run.stdout)
            return run.stdout

    def test_real_binding_compiles_around_unmanaged_env_and_preserves_contracts(self):
        output = self.compile_and_run_harness(
            r'''
#include "critical_ranger_ffm/ocean/ffm_c1_ocean_binding.h"
#include <math.h>
#include <stdio.h>

static int expect(int condition, const char *name) {
    if (!condition) fprintf(stderr, "FAIL:%s\n", name);
    return condition;
}

int main(void) {
    FfmC1OceanConfig cfg = ffm_c1_ocean_default_config();
    cfg.ffm.grid_width = 4;
    cfg.ffm.grid_height = 3;
    cfg.ffm.p = 0.0;
    cfg.ffm.f = 0.0;
    cfg.ffm.initial_tree_density = 1.0;
    cfg.ffm.episode_step_cap = 10;
    FfmC1OceanEnv env;
    int ok = expect(ffm_c1_ocean_init(&env, &cfg), "init");
    ok &= expect(env.ffm.cell_count == 12, "cell_count from real env");
    ok &= expect(env.action_count == 13, "flat grid plus noop action count");
    ok &= expect(env.obs_count == 36, "full resolution one-hot obs count");

    env.obs[0] = 99.0f;
    env.ffm.grid[0] = CR_FFM_EMPTY;
    env.ffm.grid[1] = CR_FFM_TREE;
    env.ffm.grid[2] = CR_FFM_BURNING;
    ffm_c1_ocean_write_observation(&env);
    ok &= expect(env.obs[0 * FFM_C1_OCEAN_OBS_CHANNELS + CR_FFM_EMPTY] == 1.0f, "empty one-hot");
    ok &= expect(env.obs[1 * FFM_C1_OCEAN_OBS_CHANNELS + CR_FFM_TREE] == 1.0f, "tree one-hot");
    ok &= expect(env.obs[2 * FFM_C1_OCEAN_OBS_CHANNELS + CR_FFM_BURNING] == 1.0f, "burning one-hot");
    ok &= expect(env.obs[0 * FFM_C1_OCEAN_OBS_CHANNELS + CR_FFM_TREE] == 0.0f, "observation buffer zeroed");

    for (int i = 0; i < env.ffm.cell_count; i++) env.ffm.grid[i] = CR_FFM_TREE;
    FfmC1OceanStepResult stepped = ffm_c1_ocean_step(&env, 5);
    ok &= expect(stepped.effective_intervention == 1, "tree action removes fuel");
    ok &= expect(env.ffm.grid[5] == CR_FFM_EMPTY, "selected cell remains empty after real env step");
    ok &= expect(fabsf(stepped.reward - (11.0f / 12.0f)) < 0.0001f, "living tree fraction reward");

    FfmC1OceanStepResult noop = ffm_c1_ocean_step(&env, env.action_count - 1);
    ok &= expect(noop.effective_intervention == 0, "noop is valid no intervention");
    ok &= expect(ffm_c1_ocean_decode_action(env.action_count, 4, 3).is_valid == 0, "above noop invalid");

    ffm_c1_ocean_free(&env);
    if (!ok) return 1;
    printf("real-binding-contract: PASS\n");
    return 0;
}
'''
        )
        self.assertIn("real-binding-contract: PASS", output)

    def test_binding_source_reuses_real_unmanaged_environment_not_provisional_physics(self):
        text = BINDING_SOURCE.read_text(encoding="utf-8")
        header = BINDING_HEADER.read_text(encoding="utf-8")
        self.assertIn('"../ffm_unmanaged.h"', header)
        self.assertIn("cr_ffm_init", text)
        self.assertIn("cr_ffm_step_unmanaged", text)
        self.assertNotIn("static int ffm_c1_has_burning_neighbor", text)
        self.assertNotIn("static uint64_t ffm_c1_next_u64", text)
        self.assertNotIn("dummy_reward", text)

    def test_pufferlib_staged_sources_compile_from_ocean_env_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            env_dir = tmp / "critical_ranger_ffm"
            env_dir.mkdir()
            for source in [
                PUFFER_ENV,
                PUFFER_ENV_HEADER,
                PUFFER_BINDING,
                UNMANAGED_SOURCE,
                REPO / "src" / "critical_ranger_ffm" / "ffm_unmanaged.h",
                BINDING_SOURCE,
                BINDING_HEADER,
            ]:
                (env_dir / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            (env_dir / "vecenv.h").write_text(
                "typedef float FloatTensor;\n"
                "typedef struct { float value; } DictValue;\n"
                "typedef struct Dict Dict;\n"
                "static DictValue *dict_get(Dict *d, const char *k) { (void)d; (void)k; static DictValue v = {0}; return &v; }\n"
                "static void dict_set(Dict *d, const char *k, float v) { (void)d; (void)k; (void)v; }\n",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    "cc",
                    "-std=c11",
                    "-O2",
                    "-Wall",
                    "-Wextra",
                    "-pedantic",
                    "-c",
                    "critical_ranger_ffm.c",
                    "binding.c",
                ],
                cwd=env_dir,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)

    def test_optional_render_path_draws_categorical_cells_without_mutating_env(self):
        output = self.compile_and_run_harness(
            r'''
#define CRITICAL_RANGER_FFM_ENABLE_RAYLIB_RENDER 1
#define CRITICAL_RANGER_FFM_RAYLIB_TEST_STUB 1
#include "critical_ranger_ffm/ocean/ffm_c1_ocean_binding.h"

typedef struct Color { unsigned char r; unsigned char g; unsigned char b; unsigned char a; } Color;
static const Color BLACK = {0, 0, 0, 255};
static const Color DARKGRAY = {80, 80, 80, 255};
static const Color GREEN = {0, 160, 64, 255};
static const Color ORANGE = {255, 128, 0, 255};
static int begin_calls = 0;
static int end_calls = 0;
static int clear_calls = 0;
static int empty_cells = 0;
static int tree_cells = 0;
static int burning_cells = 0;
static int outline_cells = 0;
static void BeginDrawing(void) { begin_calls++; }
static void EndDrawing(void) { end_calls++; }
static void ClearBackground(Color color) { if (color.r == BLACK.r && color.g == BLACK.g && color.b == BLACK.b) clear_calls++; }
static void DrawRectangle(int x, int y, int w, int h, Color color) {
    (void)x; (void)y; (void)w; (void)h;
    if (color.r == DARKGRAY.r && color.g == DARKGRAY.g && color.b == DARKGRAY.b) empty_cells++;
    if (color.r == GREEN.r && color.g == GREEN.g && color.b == GREEN.b) tree_cells++;
    if (color.r == ORANGE.r && color.g == ORANGE.g && color.b == ORANGE.b) burning_cells++;
}
static void DrawRectangleLines(int x, int y, int w, int h, Color color) {
    (void)x; (void)y; (void)w; (void)h; (void)color;
    outline_cells++;
}
#include "critical_ranger_ffm.h"
#include <stdio.h>

static int expect(int condition, const char *name) {
    if (!condition) fprintf(stderr, "FAIL:%s\n", name);
    return condition;
}

int main(void) {
    CriticalRangerFfm env;
    memset(&env, 0, sizeof(env));
    FfmC1OceanConfig cfg = ffm_c1_ocean_default_config();
    cfg.ffm.grid_width = 3;
    cfg.ffm.grid_height = 1;
    cfg.ffm.p = 0.0;
    cfg.ffm.f = 0.0;
    cfg.ffm.initial_tree_density = 0.0;
    cfg.ffm.episode_step_cap = 10;
    int ok = expect(ffm_c1_ocean_init(&env.ocean, &cfg), "init");
    env.initialized = 1;
    env.ocean.ffm.grid[0] = CR_FFM_EMPTY;
    env.ocean.ffm.grid[1] = CR_FFM_TREE;
    env.ocean.ffm.grid[2] = CR_FFM_BURNING;
    unsigned char before0 = env.ocean.ffm.grid[0];
    unsigned char before1 = env.ocean.ffm.grid[1];
    unsigned char before2 = env.ocean.ffm.grid[2];
    int step_before = env.ocean.ffm.step_count;
    float reward_before = 123.0f;
    float terminal_before = 0.0f;
    env.rewards = &reward_before;
    env.terminals = &terminal_before;

    c_render(&env);

    ok &= expect(begin_calls == 1, "begin drawing once");
    ok &= expect(end_calls == 1, "end drawing once");
    ok &= expect(clear_calls == 1, "clear background once");
    ok &= expect(empty_cells == 1, "draw empty cell");
    ok &= expect(tree_cells == 1, "draw tree cell");
    ok &= expect(burning_cells == 1, "draw burning cell");
    ok &= expect(outline_cells == 3, "draw cell outlines");
    ok &= expect(env.ocean.ffm.grid[0] == before0, "empty state unchanged");
    ok &= expect(env.ocean.ffm.grid[1] == before1, "tree state unchanged");
    ok &= expect(env.ocean.ffm.grid[2] == before2, "burning state unchanged");
    ok &= expect(env.ocean.ffm.step_count == step_before, "step count unchanged");
    ok &= expect(reward_before == 123.0f, "reward untouched");
    ok &= expect(terminal_before == 0.0f, "terminal untouched");

    ffm_c1_ocean_free(&env.ocean);
    if (!ok) return 1;
    printf("render-isolated-categorical: PASS\n");
    return 0;
}
'''
        )
        self.assertIn("render-isolated-categorical: PASS", output)

    def test_puffer_render_source_is_optional_and_not_step_semantics(self):
        env_header = PUFFER_ENV_HEADER.read_text(encoding="utf-8")
        self.assertIn("CRITICAL_RANGER_FFM_ENABLE_RAYLIB_RENDER", env_header)
        self.assertIn("BeginDrawing", env_header)
        self.assertIn("DrawRectangle", env_header)
        render_body = env_header.split("void c_render", 1)[1]
        self.assertNotIn("cr_ffm_step_unmanaged", render_body)
        self.assertNotIn("ffm_c1_ocean_step", render_body)
        self.assertNotIn("env->rewards", render_body)
        self.assertNotIn("env->terminals", render_body)
        self.assertNotIn("effective_interventions", render_body)

    def test_eval_render_proof_doc_separates_visual_proof_from_train_smoke(self):
        doc = RENDER_PROOF_DOC.read_text(encoding="utf-8")
        self.assertIn("Issue #20", doc)
        self.assertIn("optional raylib render path", doc)
        self.assertIn("empty", doc)
        self.assertIn("tree", doc)
        self.assertIn("burning", doc)
        self.assertIn("future ranger intervention marker", doc)
        self.assertIn("does not change physics, RNG, reward, truncation, or logged outputs", doc)
        self.assertIn("Train smoke from Issue #16", doc)
        self.assertIn("checkpoint-load smoke", doc)
        self.assertIn("visual render proof", doc)
        self.assertIn("one command at a time", doc)
        self.assertIn("Do not run Puffer, GPU, train, eval, or render commands on the VPS", doc)
        command_blocks = "\n".join(doc.split("```")[1::2])
        self.assertNotIn("puffer train", command_blocks)
        self.assertNotIn("puffer eval", command_blocks)

    def test_pufferlib_4_build_artifacts_document_real_train_wiring_scope(self):
        config_text = PUFFER_CONFIG.read_text(encoding="utf-8")
        self.assertIn("[base]", config_text)
        self.assertIn("env_name = critical_ranger_ffm", config_text)
        self.assertIn("[vec]", config_text)
        self.assertIn("total_agents = 128", config_text)
        self.assertIn("[train]", config_text)
        self.assertIn("total_timesteps = 8192", config_text)
        self.assertNotIn("PROVISIONAL", config_text)

        env_text = PUFFER_ENV.read_text(encoding="utf-8")
        env_header = PUFFER_ENV_HEADER.read_text(encoding="utf-8")
        binding_text = PUFFER_BINDING.read_text(encoding="utf-8")
        self.assertIn("ffm_c1_ocean_binding.c", env_text)
        self.assertIn("ffm_unmanaged.c", env_text)
        self.assertNotIn("ffm_c1_ocean_provisional", env_text)
        self.assertIn("ffm_c1_ocean_binding.c", binding_text)
        self.assertIn("ffm_unmanaged.c", binding_text)
        self.assertIn("#define OBS_SIZE", binding_text)
        self.assertIn("#define ACT_SIZES {128 * 128 + 1}", binding_text)
        self.assertIn("#define OBS_TENSOR_T FloatTensor", binding_text)
        self.assertIn("#include \"vecenv.h\"", binding_text)
        self.assertIn("void c_render", env_header)
        self.assertIn("Issue #20", env_header)

        doc = BUILD_DOC.read_text(encoding="utf-8")
        self.assertIn("pufferlib/config/critical_ranger_ffm.ini", doc)
        self.assertIn("bash build.sh critical_ranger_ffm --float", doc)
        self.assertIn("puffer train critical_ranger_ffm", doc)
        self.assertNotIn("puffer train critical_ranger_ffm --local", doc)
        self.assertNotIn("puffer train critical_ranger_ffm --config", doc)
        self.assertIn("one command at a time", doc)
        self.assertIn("Do not run Puffer, GPU, train, eval, or render commands on the VPS", doc)
        self.assertIn("not visual eval proof", doc)
        self.assertIn("#20", doc)
        self.assertIn("EXT_BUILD_EXIT:0", doc)
        self.assertIn("TRAIN_EXIT:0", doc)
        self.assertIn("Steps: `8.2K`", doc)
        self.assertIn("effective_interventions", doc)
        self.assertIn("build/buffer/wiring proof only", doc)


if __name__ == "__main__":
    unittest.main()
