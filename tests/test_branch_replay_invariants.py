import subprocess
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
UNMANAGED_SOURCE = REPO / "src" / "critical_ranger_ffm" / "ffm_unmanaged.c"
INCLUDE = REPO / "src" / "critical_ranger_ffm"


class BranchReplayInvariantTests(unittest.TestCase):
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
                    str(INCLUDE),
                    str(harness),
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

    def test_snapshot_restore_preserves_grid_rng_step_and_config_identity(self):
        output = self.compile_and_run_harness(
            r'''
#include "ffm_unmanaged.h"
#include <stdio.h>
#include <string.h>

static int expect(int condition, const char *name) {
    if (!condition) fprintf(stderr, "FAIL:%s\n", name);
    return condition;
}

int main(void) {
    CrFfmConfig cfg = cr_ffm_default_config();
    cfg.grid_width = 4;
    cfg.grid_height = 3;
    cfg.seed = 3401;
    cfg.p = 0.2;
    cfg.f = 0.1;
    cfg.initial_tree_density = 0.5;
    cfg.episode_step_cap = 20;

    CrFfmEnv env;
    int ok = expect(cr_ffm_init(&env, &cfg), "init");
    cr_ffm_step_unmanaged(&env);
    env.grid[2] = CR_FFM_BURNING;

    CrFfmSnapshot snapshot;
    ok &= expect(cr_ffm_snapshot_init(&snapshot, &env), "snapshot init");
    unsigned char saved_grid[12];
    memcpy(saved_grid, env.grid, sizeof(saved_grid));
    uint64_t saved_rng = env.rng.state;
    int saved_step = env.step_count;

    cr_ffm_step_unmanaged(&env);
    env.grid[0] = CR_FFM_EMPTY;
    ok &= expect(!cr_ffm_env_matches_snapshot(&env, &snapshot), "mutated env no longer matches snapshot");
    ok &= expect(cr_ffm_restore(&env, &snapshot), "restore");
    ok &= expect(cr_ffm_env_matches_snapshot(&env, &snapshot), "env matches restored snapshot");
    ok &= expect(memcmp(env.grid, saved_grid, sizeof(saved_grid)) == 0, "grid restored exactly");
    ok &= expect(env.rng.state == saved_rng, "rng restored exactly");
    ok &= expect(env.step_count == saved_step, "step restored exactly");
    ok &= expect(env.cfg.seed == cfg.seed && env.cfg.p == cfg.p && env.cfg.f == cfg.f, "config identity restored");

    cr_ffm_snapshot_free(&snapshot);
    cr_ffm_free(&env);
    if (!ok) return 1;
    printf("snapshot-restore: PASS\n");
    return 0;
}
'''
        )
        self.assertIn("snapshot-restore: PASS", output)

    def test_replay_tape_shares_regrowth_and_lightning_schedule_across_branches(self):
        output = self.compile_and_run_harness(
            r'''
#include "ffm_unmanaged.h"
#include <stdio.h>
#include <string.h>

static int expect(int condition, const char *name) {
    if (!condition) fprintf(stderr, "FAIL:%s\n", name);
    return condition;
}

int main(void) {
    CrFfmConfig cfg = cr_ffm_default_config();
    cfg.grid_width = 3;
    cfg.grid_height = 1;
    cfg.seed = 3402;
    cfg.p = 1.0;
    cfg.f = 1.0;
    cfg.initial_tree_density = 0.0;
    cfg.episode_step_cap = 10;

    CrFfmEnv treatment;
    CrFfmEnv control;
    int ok = expect(cr_ffm_init(&treatment, &cfg), "init treatment");
    ok &= expect(cr_ffm_init(&control, &cfg), "init control");
    treatment.grid[0] = CR_FFM_TREE;
    treatment.grid[1] = CR_FFM_EMPTY;
    treatment.grid[2] = CR_FFM_TREE;
    memcpy(control.grid, treatment.grid, 3);

    CrFfmSnapshot snapshot;
    ok &= expect(cr_ffm_snapshot_init(&snapshot, &treatment), "snapshot init");
    CrFfmReplayTape tape;
    ok &= expect(cr_ffm_replay_tape_init(&tape, &snapshot, 2), "replay init");
    cr_ffm_restore(&treatment, &snapshot);
    cr_ffm_restore(&control, &snapshot);

    treatment.grid[0] = CR_FFM_EMPTY;
    control.grid[2] = CR_FFM_EMPTY;

    CrFfmStepResult treatment_step = cr_ffm_step_unmanaged_with_replay(&treatment, &tape, 0, NULL);
    CrFfmStepResult control_step = cr_ffm_step_unmanaged_with_replay(&control, &tape, 0, NULL);

    ok &= expect(treatment_step.regrowths == control_step.regrowths, "branches share regrowth count");
    ok &= expect(treatment_step.lightning_ignitions == control_step.lightning_ignitions, "branches share lightning count");
    ok &= expect(treatment.rng.state == snapshot.rng.state, "replay does not consume treatment rng");
    ok &= expect(control.rng.state == snapshot.rng.state, "replay does not consume control rng");
    ok &= expect(treatment.grid[1] == control.grid[1], "same cell sees same replayed stochastic future");

    cr_ffm_replay_tape_free(&tape);
    cr_ffm_snapshot_free(&snapshot);
    cr_ffm_free(&treatment);
    cr_ffm_free(&control);
    if (!ok) return 1;
    printf("shared-replay: PASS\n");
    return 0;
}
'''
        )
        self.assertIn("shared-replay: PASS", output)

    def test_branch_invariant_allows_only_intended_intervention_cell_and_flags_invalid_pair(self):
        output = self.compile_and_run_harness(
            r'''
#include "ffm_unmanaged.h"
#include <stdio.h>
#include <string.h>

static int expect(int condition, const char *name) {
    if (!condition) fprintf(stderr, "FAIL:%s reason=%d mismatches=%d first=%d\n", name, 0, 0, 0);
    return condition;
}

int main(void) {
    CrFfmConfig cfg = cr_ffm_default_config();
    cfg.grid_width = 2;
    cfg.grid_height = 2;
    cfg.seed = 3403;
    cfg.p = 0.0;
    cfg.f = 0.0;
    cfg.initial_tree_density = 1.0;
    cfg.episode_step_cap = 10;

    CrFfmEnv treatment;
    CrFfmEnv control;
    int ok = expect(cr_ffm_init(&treatment, &cfg), "init treatment");
    ok &= expect(cr_ffm_init(&control, &cfg), "init control");
    for (int i = 0; i < 4; i++) {
        treatment.grid[i] = CR_FFM_TREE;
        control.grid[i] = CR_FFM_TREE;
    }

    treatment.grid[1] = CR_FFM_EMPTY;
    CrFfmBranchInvariantResult allowed = cr_ffm_check_branch_invariant(&treatment, &control, 1);
    ok &= expect(allowed.valid, "single intended intervention difference is valid");
    ok &= expect(allowed.mismatch_count == 1 && allowed.first_mismatch == 1, "intended mismatch recorded");

    control.grid[2] = CR_FFM_EMPTY;
    CrFfmBranchInvariantResult invalid = cr_ffm_check_branch_invariant(&treatment, &control, 1);
    ok &= expect(!invalid.valid, "extra branch difference invalidates pair");
    ok &= expect(invalid.reason == CR_FFM_BRANCH_INVARIANT_GRID_MISMATCH, "extra grid difference reason");
    ok &= expect(invalid.mismatch_count == 2, "extra mismatch counted for quarantine/hard stop");

    control.grid[2] = CR_FFM_TREE;
    control.rng.state += 1;
    CrFfmBranchInvariantResult rng_invalid = cr_ffm_check_branch_invariant(&treatment, &control, 1);
    ok &= expect(!rng_invalid.valid, "rng divergence invalidates pair");
    ok &= expect(rng_invalid.reason == CR_FFM_BRANCH_INVARIANT_RNG_MISMATCH, "rng mismatch reason");

    cr_ffm_free(&treatment);
    cr_ffm_free(&control);
    if (!ok) return 1;
    printf("branch-invariants: PASS\n");
    return 0;
}
'''
        )
        self.assertIn("branch-invariants: PASS", output)


if __name__ == "__main__":
    unittest.main()
