import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from critical_ranger_ffm.reporting.report_fire_sizes import write_report


class ReportFireSizesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.clusters = self.tmp / "clusters.csv"
        self.interventions = self.tmp / "interventions.csv"
        self.out_dir = self.tmp / "reports"

    def write_csv(self, path, fieldnames, rows):
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def test_report_creates_plots_and_summary_with_small_sample_warnings(self):
        cluster_fields = [
            "schema_version",
            "run_id",
            "mode",
            "seed",
            "episode_id",
            "step",
            "event_id",
            "cluster_id",
            "fire_size",
            "grid_width",
            "grid_height",
            "p",
            "f",
            "global_tree_density",
            "quiet_window_component_count",
            "overlap_signal",
            "pair_id",
            "source",
            "notes",
        ]
        rows = []
        sizes = [1, 2, 3, 5, 8, 13, 21, 34]
        for index, size in enumerate(sizes, start=1):
            rows.append(
                {
                    "schema_version": "1",
                    "run_id": "fixture-baseline",
                    "mode": "baseline",
                    "seed": "101",
                    "episode_id": "0",
                    "step": str(index * 1000),
                    "event_id": str(index),
                    "cluster_id": str(index),
                    "fire_size": str(size),
                    "grid_width": "128",
                    "grid_height": "128",
                    "p": "0.01",
                    "f": "0.000001",
                    "global_tree_density": "0.55",
                    "quiet_window_component_count": "1",
                    "overlap_signal": "single_component",
                    "pair_id": "",
                    "source": "synthetic",
                    "notes": "",
                }
            )
        self.write_csv(self.clusters, cluster_fields, rows)

        intervention_fields = [
            "schema_version",
            "pair_id",
            "run_id",
            "mode",
            "seed",
            "episode_id",
            "intervention_step",
            "action_row",
            "action_col",
            "selected_cell_state",
            "effective_intervention",
            "local_fuel_density",
            "density_bucket",
            "matched_control_for_pair_id",
            "post_intervention_seed",
            "downstream_window_steps",
            "source",
            "notes",
        ]
        self.write_csv(self.interventions, intervention_fields, [])

        result = write_report(self.clusters, self.interventions, self.out_dir)

        self.assertTrue((self.out_dir / "fire_size_loglog.png").exists())
        self.assertTrue((self.out_dir / "intervention_shift.png").exists())
        self.assertIn("mode", result.summary_table)
        self.assertIn("baseline", result.summary_table)
        self.assertTrue(any("small sample" in warning for warning in result.warnings), result.warnings)
        self.assertTrue(any("no paired intervention rows" in warning for warning in result.warnings), result.warnings)

    def test_module_cli_runs_against_committed_fixtures(self):
        repo = Path(__file__).resolve().parents[1]
        output_dir = self.tmp / "fixture-report"
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "critical_ranger_ffm.reporting.report_fire_sizes",
                "--clusters",
                "data/fixtures/cluster_close_sample.csv",
                "--interventions",
                "data/fixtures/intervention_sample.csv",
                "--config",
                "configs/reporting.default.json",
                "--out-dir",
                str(output_dir),
            ],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        self.assertIn("baseline", completed.stdout)
        self.assertTrue((output_dir / "fire_size_loglog.png").exists())
        self.assertTrue((output_dir / "intervention_shift.png").exists())


if __name__ == "__main__":
    unittest.main()
