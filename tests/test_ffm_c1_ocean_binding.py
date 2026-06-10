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
PUFFER_BINDING = REPO / "pufferlib" / "ocean" / "critical_ranger_ffm" / "binding.c"
BUILD_DOC = REPO / "docs" / "references" / "pufferlib-c1-real-binding-build.md"


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
                PUFFER_BINDING,
                UNMANAGED_SOURCE,
                REPO / "src" / "critical_ranger_ffm" / "ffm_unmanaged.h",
                BINDING_SOURCE,
                BINDING_HEADER,
            ]:
                (env_dir / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
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
        binding_text = PUFFER_BINDING.read_text(encoding="utf-8")
        self.assertIn("ffm_c1_ocean_binding.c", env_text)
        self.assertIn("ffm_unmanaged.c", env_text)
        self.assertNotIn("ffm_c1_ocean_provisional", env_text)
        self.assertIn("c_render", binding_text)
        self.assertIn("deferred to Issue #20", binding_text)
        self.assertIn("not visual eval proof", binding_text)

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


if __name__ == "__main__":
    unittest.main()
