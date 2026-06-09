import hashlib
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "src" / "critical_ranger_ffm" / "ffm_unmanaged.c"
INCLUDE = REPO / "src" / "critical_ranger_ffm"


class FfmUnmanagedEnvTests(unittest.TestCase):
    def compile_and_run(self, c_source: str):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            harness = tmp / "harness.c"
            binary = tmp / "harness"
            harness.write_text(textwrap.dedent(c_source), encoding="utf-8")
            compiled = subprocess.run(
                [
                    "cc",
                    "-std=c11",
                    "-O2",
                    "-Wall",
                    "-Wextra",
                    "-pedantic",
                    "-I",
                    str(INCLUDE),
                    str(harness),
                    str(SOURCE),
                    "-o",
                    str(binary),
                ],
                cwd=REPO,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr + compiled.stdout)
            completed = subprocess.run(
                [str(binary)],
                cwd=REPO,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            return completed.stdout

    def test_unmanaged_snapshot_spread_burnout_and_no_cascade(self):
        stdout = self.compile_and_run(
            r'''
            #include "ffm_unmanaged.h"
            #include <stdio.h>

            static int require(int condition, const char *message) {
                if (!condition) {
                    fprintf(stderr, "%s\n", message);
                    return 0;
                }
                return 1;
            }

            int main(void) {
                CrFfmConfig cfg = cr_ffm_default_config();
                cfg.grid_width = 3;
                cfg.grid_height = 3;
                cfg.p = 0.0;
                cfg.f = 0.0;
                cfg.initial_tree_density = 0.0;
                cfg.episode_step_cap = 10;
                CrFfmEnv env;
                if (!cr_ffm_init(&env, &cfg)) return 2;
                for (int i = 0; i < env.cell_count; i++) env.grid[i] = CR_FFM_TREE;
                env.grid[4] = CR_FFM_BURNING;

                CrFfmStepResult result = cr_ffm_step_unmanaged(&env);
                int ok = 1;
                ok &= require(result.active_before == 1, "active_before counts snapshot burning cells");
                ok &= require(result.active_after == 4, "only orthogonal neighbors ignite");
                ok &= require(env.grid[4] == CR_FFM_EMPTY, "snapshot burning cell burns out same tick");
                ok &= require(env.grid[1] == CR_FFM_BURNING && env.grid[3] == CR_FFM_BURNING &&
                              env.grid[5] == CR_FFM_BURNING && env.grid[7] == CR_FFM_BURNING,
                              "orthogonal tree neighbors become burning");
                ok &= require(env.grid[0] == CR_FFM_TREE && env.grid[2] == CR_FFM_TREE &&
                              env.grid[6] == CR_FFM_TREE && env.grid[8] == CR_FFM_TREE,
                              "diagonal cells do not ignite by in-place cascade");
                cr_ffm_free(&env);
                return ok ? 0 : 1;
            }
            '''
        )
        self.assertEqual(stdout, "")

    def test_regrowth_and_lightning_continue_during_active_fires(self):
        stdout = self.compile_and_run(
            r'''
            #include "ffm_unmanaged.h"
            #include <stdio.h>

            static int require(int condition, const char *message) {
                if (!condition) {
                    fprintf(stderr, "%s\n", message);
                    return 0;
                }
                return 1;
            }

            int main(void) {
                int ok = 1;
                CrFfmConfig regrow_cfg = cr_ffm_default_config();
                regrow_cfg.grid_width = 3;
                regrow_cfg.grid_height = 1;
                regrow_cfg.p = 1.0;
                regrow_cfg.f = 0.0;
                regrow_cfg.initial_tree_density = 0.0;
                regrow_cfg.episode_step_cap = 5;
                CrFfmEnv regrow_env;
                if (!cr_ffm_init(&regrow_env, &regrow_cfg)) return 2;
                regrow_env.grid[0] = CR_FFM_BURNING;
                regrow_env.grid[1] = CR_FFM_EMPTY;
                regrow_env.grid[2] = CR_FFM_EMPTY;
                CrFfmStepResult regrow = cr_ffm_step_unmanaged(&regrow_env);
                ok &= require(regrow.active_before == 1, "regrowth case starts with an active fire");
                ok &= require(regrow.regrowths == 2, "regrowth is not suppressed during active fires");
                ok &= require(regrow_env.grid[0] == CR_FFM_EMPTY, "active fire burns out in regrowth case");
                ok &= require(regrow_env.grid[1] == CR_FFM_BURNING, "newly regrown orthogonal neighbor can ignite synchronously");
                ok &= require(regrow_env.grid[2] == CR_FFM_TREE, "newly regrown non-neighbor remains tree");
                cr_ffm_free(&regrow_env);

                CrFfmConfig lightning_cfg = cr_ffm_default_config();
                lightning_cfg.grid_width = 3;
                lightning_cfg.grid_height = 1;
                lightning_cfg.p = 0.0;
                lightning_cfg.f = 1.0;
                lightning_cfg.initial_tree_density = 0.0;
                lightning_cfg.episode_step_cap = 5;
                CrFfmEnv lightning_env;
                if (!cr_ffm_init(&lightning_env, &lightning_cfg)) return 2;
                lightning_env.grid[0] = CR_FFM_BURNING;
                lightning_env.grid[1] = CR_FFM_EMPTY;
                lightning_env.grid[2] = CR_FFM_TREE;
                CrFfmStepResult lightning = cr_ffm_step_unmanaged(&lightning_env);
                ok &= require(lightning.active_before == 1, "lightning case starts with an active fire");
                ok &= require(lightning.lightning_ignitions == 1, "lightning is not suppressed during active fires");
                ok &= require(lightning_env.grid[0] == CR_FFM_EMPTY && lightning_env.grid[2] == CR_FFM_EMPTY,
                              "snapshot burning and lightning-ignited cells burn out same tick");
                cr_ffm_free(&lightning_env);
                return ok ? 0 : 1;
            }
            '''
        )
        self.assertEqual(stdout, "")

    def test_same_seed_and_config_replay_identical_grid_evolution(self):
        stdout = self.compile_and_run(
            r'''
            #include "ffm_unmanaged.h"
            #include <stdio.h>
            #include <stdint.h>

            static uint64_t digest_env(const CrFfmEnv *env, uint64_t digest) {
                for (int i = 0; i < env->cell_count; i++) {
                    digest ^= (uint64_t)(env->grid[i] + 1u);
                    digest *= 1099511628211ULL;
                }
                return digest;
            }

            static uint64_t run_once(void) {
                CrFfmConfig cfg = cr_ffm_default_config();
                cfg.grid_width = 8;
                cfg.grid_height = 8;
                cfg.p = 0.07;
                cfg.f = 0.03;
                cfg.seed = 424242ULL;
                cfg.initial_tree_density = 0.41;
                cfg.episode_step_cap = 200;
                CrFfmEnv env;
                if (!cr_ffm_init(&env, &cfg)) return 0;
                uint64_t digest = 1469598103934665603ULL;
                for (int step = 0; step < 40; step++) {
                    CrFfmStepResult result = cr_ffm_step_unmanaged(&env);
                    digest = digest_env(&env, digest ^ (uint64_t)result.lightning_ignitions);
                }
                cr_ffm_free(&env);
                return digest;
            }

            int main(void) {
                uint64_t first = run_once();
                uint64_t second = run_once();
                if (first == 0 || first != second) {
                    fprintf(stderr, "replay mismatch: %llu vs %llu\n",
                            (unsigned long long)first,
                            (unsigned long long)second);
                    return 1;
                }
                printf("%llu\n", (unsigned long long)first);
                return 0;
            }
            '''
        )
        digest = stdout.strip()
        self.assertTrue(digest.isdigit())
        self.assertNotEqual(hashlib.sha256(digest.encode()).hexdigest(), "")


if __name__ == "__main__":
    unittest.main()
