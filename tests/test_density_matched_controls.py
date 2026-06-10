import subprocess
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
UNMANAGED_SOURCE = REPO / "src" / "critical_ranger_ffm" / "ffm_unmanaged.c"
INCLUDE = REPO / "src" / "critical_ranger_ffm"


class DensityMatchedControlTests(unittest.TestCase):
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

    def test_selects_valid_same_timestep_7x7_tercile_match_with_diagnostics(self):
        output = self.compile_and_run_harness(
            r'''
#include "ffm_unmanaged.h"
#include <stdio.h>

static int expect(int condition, const char *name) {
    if (!condition) fprintf(stderr, "FAIL:%s\n", name);
    return condition;
}

int main(void) {
    CrFfmConfig cfg = cr_ffm_default_config();
    cfg.grid_width = 5;
    cfg.grid_height = 5;
    cfg.seed = 3501;
    cfg.initial_tree_density = 1.0;
    CrFfmEnv env;
    int ok = expect(cr_ffm_init(&env, &cfg), "init");
    env.step_count = 17;

    CrFfmControlMatch match = cr_ffm_select_density_matched_control(&env, 12, 9001);
    ok &= expect(match.valid, "valid match");
    ok &= expect(match.ranger_index == 12, "ranger index recorded");
    ok &= expect(match.control_index >= 0 && match.control_index < env.cell_count, "control index in grid");
    ok &= expect(match.control_index != 12, "ranger cell excluded");
    ok &= expect(match.ranger_tercile == CR_FFM_DENSITY_TERCILE_HIGH, "ranger high tercile");
    ok &= expect(match.control_tercile == match.ranger_tercile, "same tercile");
    ok &= expect(match.ranger_density_numerator == 24 && match.ranger_density_denominator == 24, "ranger density diagnostics");
    ok &= expect(match.control_density_numerator == match.control_density_denominator, "control density diagnostics");
    ok &= expect(match.total_candidate_count == 24, "candidate count excludes ranger");
    ok &= expect(match.same_tercile_candidate_count == 24, "same-tercile candidate count");
    ok &= expect(match.seed == 9001 && match.timestep == 17, "seed and timestep diagnostics");

    cr_ffm_free(&env);
    if (!ok) return 1;
    printf("valid-density-match: PASS\n");
    return 0;
}
'''
        )
        self.assertIn("valid-density-match: PASS", output)

    def test_no_same_tercile_control_is_invalid_without_relaxing_match(self):
        output = self.compile_and_run_harness(
            r'''
#include "ffm_unmanaged.h"
#include <stdio.h>

static int expect(int condition, const char *name) {
    if (!condition) fprintf(stderr, "FAIL:%s\n", name);
    return condition;
}

int main(void) {
    CrFfmConfig cfg = cr_ffm_default_config();
    cfg.grid_width = 5;
    cfg.grid_height = 5;
    cfg.seed = 3502;
    cfg.initial_tree_density = 0.0;
    CrFfmEnv env;
    int ok = expect(cr_ffm_init(&env, &cfg), "init");
    int ranger = 12;
    int candidate_cells[] = {0, 1, 2, 3, 5, 10, 15};
    env.grid[ranger] = CR_FFM_TREE;
    for (int i = 0; i < 7; i++) env.grid[candidate_cells[i]] = CR_FFM_TREE;
    env.step_count = 23;

    CrFfmControlMatch match = cr_ffm_select_density_matched_control(&env, ranger, 9002);
    ok &= expect(!match.valid, "invalid when no same-tercile control exists");
    ok &= expect(match.control_index == -1, "no selected control");
    ok &= expect(match.invalid_reason == CR_FFM_CONTROL_MATCH_NO_SAME_TERCILE_CONTROL, "clear no-match reason");
    ok &= expect(match.total_candidate_count == 7, "candidate trees exist but are not relaxed into matches");
    ok &= expect(match.same_tercile_candidate_count == 0, "no same-tercile candidates");
    ok &= expect(match.ranger_density_numerator == 7 && match.ranger_density_denominator == 24, "ranger density diagnosed");
    ok &= expect(match.ranger_tercile == CR_FFM_DENSITY_TERCILE_LOW, "ranger tercile still diagnosed");
    ok &= expect(match.seed == 9002 && match.timestep == 23, "seed and timestep retained on invalid");

    cr_ffm_free(&env);
    if (!ok) return 1;
    printf("no-same-tercile-invalid: PASS\n");
    return 0;
}
'''
        )
        self.assertIn("no-same-tercile-invalid: PASS", output)

    def test_ranger_cell_is_excluded_even_when_it_is_the_only_matching_tree(self):
        output = self.compile_and_run_harness(
            r'''
#include "ffm_unmanaged.h"
#include <stdio.h>

static int expect(int condition, const char *name) {
    if (!condition) fprintf(stderr, "FAIL:%s\n", name);
    return condition;
}

int main(void) {
    CrFfmConfig cfg = cr_ffm_default_config();
    cfg.grid_width = 1;
    cfg.grid_height = 2;
    cfg.seed = 3503;
    cfg.initial_tree_density = 0.0;
    CrFfmEnv env;
    int ok = expect(cr_ffm_init(&env, &cfg), "init");
    env.grid[0] = CR_FFM_TREE;
    env.grid[1] = CR_FFM_EMPTY;

    CrFfmControlMatch match = cr_ffm_select_density_matched_control(&env, 0, 9003);
    ok &= expect(!match.valid, "cannot self-match ranger cell");
    ok &= expect(match.control_index == -1, "no control selected");
    ok &= expect(match.total_candidate_count == 0, "non-tree and ranger cells excluded");

    cr_ffm_free(&env);
    if (!ok) return 1;
    printf("ranger-excluded: PASS\n");
    return 0;
}
'''
        )
        self.assertIn("ranger-excluded: PASS", output)

    def test_boundary_7x7_window_clips_to_grid_and_excludes_center_cell(self):
        output = self.compile_and_run_harness(
            r'''
#include "ffm_unmanaged.h"
#include <stdio.h>

static int expect(int condition, const char *name) {
    if (!condition) fprintf(stderr, "FAIL:%s\n", name);
    return condition;
}

int main(void) {
    CrFfmConfig cfg = cr_ffm_default_config();
    cfg.grid_width = 5;
    cfg.grid_height = 5;
    cfg.seed = 3504;
    cfg.initial_tree_density = 0.0;
    CrFfmEnv env;
    int ok = expect(cr_ffm_init(&env, &cfg), "init");
    for (int i = 0; i < env.cell_count; i++) env.grid[i] = CR_FFM_TREE;

    int tree_count = -1;
    int cell_count = -1;
    CrFfmDensityTercile tercile = CR_FFM_DENSITY_TERCILE_INVALID;
    ok &= expect(cr_ffm_measure_local_tree_density_7x7(&env, 0, &tree_count, &cell_count, &tercile), "corner density measured");
    ok &= expect(tree_count == 15 && cell_count == 15, "corner clipped 4x4 window excluding center");
    ok &= expect(tercile == CR_FFM_DENSITY_TERCILE_HIGH, "corner high tercile");

    ok &= expect(cr_ffm_measure_local_tree_density_7x7(&env, 12, &tree_count, &cell_count, &tercile), "center density measured");
    ok &= expect(tree_count == 24 && cell_count == 24, "center 5x5 window excluding center on small grid");

    cr_ffm_free(&env);
    if (!ok) return 1;
    printf("boundary-window: PASS\n");
    return 0;
}
'''
        )
        self.assertIn("boundary-window: PASS", output)

    def test_tie_selection_is_reproducible_from_pair_seed_and_grid_state(self):
        output = self.compile_and_run_harness(
            r'''
#include "ffm_unmanaged.h"
#include <stdio.h>

static int expect(int condition, const char *name) {
    if (!condition) fprintf(stderr, "FAIL:%s\n", name);
    return condition;
}

int main(void) {
    CrFfmConfig cfg = cr_ffm_default_config();
    cfg.grid_width = 4;
    cfg.grid_height = 4;
    cfg.seed = 3505;
    cfg.initial_tree_density = 1.0;
    CrFfmEnv env;
    int ok = expect(cr_ffm_init(&env, &cfg), "init");

    CrFfmControlMatch first = cr_ffm_select_density_matched_control(&env, 5, 42);
    CrFfmControlMatch second = cr_ffm_select_density_matched_control(&env, 5, 42);
    CrFfmControlMatch changed_seed = cr_ffm_select_density_matched_control(&env, 5, 43);

    ok &= expect(first.valid && second.valid && changed_seed.valid, "all ties produce valid matches");
    ok &= expect(first.control_index == second.control_index, "same pair seed is reproducible");
    ok &= expect(first.same_tercile_candidate_count > 1, "tie set has multiple candidates");
    ok &= expect(first.control_index != 5 && changed_seed.control_index != 5, "tie never selects ranger cell");
    ok &= expect(first.control_index != changed_seed.control_index, "pair seed participates in tie break");

    cr_ffm_free(&env);
    if (!ok) return 1;
    printf("tie-reproducible: PASS\n");
    return 0;
}
'''
        )
        self.assertIn("tie-reproducible: PASS", output)


if __name__ == "__main__":
    unittest.main()
