import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "src" / "critical_ranger_ffm" / "ffm_unmanaged.c"
INCLUDE = REPO / "src" / "critical_ranger_ffm"


class FfmHoshenKopelmanClusterTests(unittest.TestCase):
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

    def test_hk_labels_empty_single_and_multiple_4_neighbor_components(self):
        stdout = self.compile_and_run(
            r'''
            #include "ffm_unmanaged.h"
            #include <stdio.h>
            #include <string.h>

            static int require(int condition, const char *message) {
                if (!condition) {
                    fprintf(stderr, "%s\n", message);
                    return 0;
                }
                return 1;
            }

            int main(void) {
                int labels[12];
                int sizes[12];
                CrFfmClusterSummary summary;
                int ok = 1;

                unsigned char empty[12] = {0};
                memset(labels, -1, sizeof(labels));
                memset(sizes, 0, sizeof(sizes));
                ok &= require(cr_ffm_hk_label_burned_mask(empty, 4, 3, CR_FFM_CONNECTIVITY_4,
                                                          labels, sizes, 12, &summary) == 1,
                              "empty burned mask labels successfully");
                ok &= require(summary.component_count == 0, "empty mask has zero components");
                ok &= require(summary.total_burned == 0, "empty mask has zero burned cells");
                ok &= require(summary.largest_component_size == 0, "empty mask largest size is zero");

                unsigned char one[12] = {
                    1, 1, 0, 0,
                    0, 1, 0, 0,
                    0, 0, 0, 0,
                };
                memset(labels, -1, sizeof(labels));
                memset(sizes, 0, sizeof(sizes));
                ok &= require(cr_ffm_hk_label_burned_mask(one, 4, 3, CR_FFM_CONNECTIVITY_4,
                                                          labels, sizes, 12, &summary) == 1,
                              "single component labels successfully");
                ok &= require(summary.component_count == 1, "single component count");
                ok &= require(summary.total_burned == 3, "single component total burned");
                ok &= require(summary.largest_component_size == 3, "single component largest size");
                ok &= require(sizes[0] == 3, "single component size is stored");

                unsigned char multiple[12] = {
                    1, 0, 1, 1,
                    1, 0, 0, 1,
                    0, 1, 0, 0,
                };
                memset(labels, -1, sizeof(labels));
                memset(sizes, 0, sizeof(sizes));
                ok &= require(cr_ffm_hk_label_burned_mask(multiple, 4, 3, CR_FFM_CONNECTIVITY_4,
                                                          labels, sizes, 12, &summary) == 1,
                              "multiple components label successfully");
                ok &= require(summary.component_count == 3, "multiple component count");
                ok &= require(summary.total_burned == 6, "multiple total burned");
                ok &= require(summary.largest_component_size == 3, "multiple largest component");
                ok &= require(labels[0] == labels[4], "orthogonal cells share a label");
                ok &= require(labels[0] != labels[2], "separated cells do not share a label");
                ok &= require(labels[2] == labels[3] && labels[3] == labels[7], "right-side orthogonal component shares a label");
                ok &= require(labels[9] != labels[4], "diagonal-only contact does not connect components");

                return ok ? 0 : 1;
            }
            '''
        )
        self.assertEqual(stdout, "")

    def test_connectivity_contract_rejects_mismatch_between_spread_and_cluster_labeling(self):
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
                unsigned char diagonal_only[4] = {1, 0, 0, 1};
                int labels[4];
                int sizes[4];
                CrFfmClusterSummary summary;
                int ok = 1;

                CrFfmConfig cfg = cr_ffm_default_config();
                ok &= require(cfg.connectivity == CR_FFM_CONNECTIVITY_4,
                              "default config uses the only supported connectivity");
                cfg.connectivity = 8;
                ok &= require(cr_ffm_validate_config(&cfg) == 0,
                              "unsupported spread/connectivity mismatch fails config validation");

                ok &= require(cr_ffm_hk_label_burned_mask(diagonal_only, 2, 2, CR_FFM_CONNECTIVITY_4,
                                                          labels, sizes, 4, &summary) == 1,
                              "4-neighbor diagonal mask labels successfully");
                ok &= require(summary.component_count == 2,
                              "diagonal-only burned cells stay separate under spread-matching connectivity");
                ok &= require(cr_ffm_hk_label_burned_mask(diagonal_only, 2, 2, 8,
                                                          labels, sizes, 4, &summary) == 0,
                              "unsupported 8-neighbor labeling fails clearly");
                return ok ? 0 : 1;
            }
            '''
        )
        self.assertEqual(stdout, "")

    def test_quiet_window_is_required_but_cluster_size_comes_from_burned_mask_connectivity(self):
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
                cfg.grid_width = 4;
                cfg.grid_height = 3;
                cfg.p = 0.0;
                cfg.f = 0.0;
                cfg.initial_tree_density = 0.0;
                cfg.episode_step_cap = 10;
                CrFfmEnv env;
                int ok = 1;
                if (!cr_ffm_init(&env, &cfg)) return 2;

                env.grid[0] = CR_FFM_BURNING;
                ok &= require(cr_ffm_can_label_fire_clusters(&env) == 0,
                              "active burning grid is not a safe quiet-window labeling moment");
                env.grid[0] = CR_FFM_EMPTY;
                ok &= require(cr_ffm_can_label_fire_clusters(&env) == 1,
                              "quiet grid is safe to label");

                unsigned char burned_mask[12] = {
                    1, 1, 0, 0,
                    0, 1, 0, 1,
                    0, 0, 0, 1,
                };
                int labels[12];
                int sizes[12];
                CrFfmClusterSummary summary;
                ok &= require(cr_ffm_hk_label_burned_mask(burned_mask, 4, 3, env.cfg.connectivity,
                                                          labels, sizes, 12, &summary) == 1,
                              "quiet-window burned mask labels successfully");
                ok &= require(summary.component_count == 2,
                              "whole fire is split by burned-mask connectivity, not quiet-window timing");
                ok &= require(summary.total_burned == 5,
                              "whole-fire size comes from connected burned cells");
                ok &= require(summary.largest_component_size == 3,
                              "largest connected burned component is reported");
                cr_ffm_free(&env);
                return ok ? 0 : 1;
            }
            '''
        )
        self.assertEqual(stdout, "")


if __name__ == "__main__":
    unittest.main()
