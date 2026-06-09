import csv
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from critical_ranger_ffm.reporting.report_fire_sizes import REQUIRED_CLUSTER_COLUMNS, load_cluster_rows


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "demos" / "ffm_baseline_smoke.c"
CONFIG = REPO / "configs" / "ffm_baseline_smoke.ini"


class FfmBaselineSmokeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.binary = self.tmp / "ffm_baseline_smoke"

    def compile_demo(self):
        completed = subprocess.run(
            ["cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-pedantic", str(SOURCE), "-lm", "-o", str(self.binary)],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)

    def run_demo(self, *args):
        self.compile_demo()
        completed = subprocess.run(
            [str(self.binary), *args],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        return completed

    def test_self_tests_cover_sync_spread_burnout_hk_and_determinism_primitives(self):
        completed = self.run_demo("--self-test")
        self.assertIn("self-test: PASS", completed.stdout)

    def test_default_config_pins_measurement_grid_and_warmup_policy(self):
        text = CONFIG.read_text(encoding="utf-8")
        self.assertIn("grid_width=128", text)
        self.assertIn("grid_height=128", text)
        self.assertIn("min_gate_grid_size=128", text)
        self.assertIn("warmup_steps=", text)

    def test_smoke_run_writes_part_b_cluster_csv_and_auditable_summary(self):
        out_csv = self.tmp / "clusters.csv"
        summary_json = self.tmp / "summary.json"
        self.run_demo(
            "--config", str(CONFIG),
            "--out", str(out_csv),
            "--summary", str(summary_json),
            "--grid-width", "32",
            "--grid-height", "32",
            "--min-gate-grid-size", "32",
            "--warmup-steps", "20",
            "--cluster-target", "5",
            "--max-steps", "50000",
            "--p", "0.05",
            "--f", "0.0001",
            "--seed", "123",
        )

        with out_csv.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            self.assertEqual(reader.fieldnames, REQUIRED_CLUSTER_COLUMNS)
        rows = load_cluster_rows(out_csv)
        self.assertGreaterEqual(len(rows), 5)
        self.assertTrue(all(row["mode"] == "baseline" for row in rows))
        self.assertTrue(all(row["source"] == "env" for row in rows))

        summary = json.loads(summary_json.read_text(encoding="utf-8"))
        self.assertEqual(summary["grid_width"], 32)
        self.assertEqual(summary["grid_height"], 32)
        self.assertEqual(summary["warmup_steps_used"], 20)
        self.assertGreater(summary["density_samples_after_warmup"], 0)
        self.assertIn("critical_density_mean", summary)
        self.assertIn("critical_density_band_min", summary)
        self.assertIn("critical_density_band_max", summary)
        self.assertIn(summary["measurement_grid_gate"], ["pass", "warn"])

    def test_same_seed_replay_writes_identical_cluster_csv(self):
        def run_once(name):
            out_csv = self.tmp / f"{name}.csv"
            summary_json = self.tmp / f"{name}.json"
            self.run_demo(
                "--config", str(CONFIG),
                "--out", str(out_csv),
                "--summary", str(summary_json),
                "--grid-width", "32",
                "--grid-height", "32",
                "--min-gate-grid-size", "32",
                "--warmup-steps", "20",
                "--cluster-target", "8",
                "--max-steps", "5000",
                "--p", "0.05",
                "--f", "0.001",
                "--seed", "777",
            )
            return hashlib.sha256(out_csv.read_bytes()).hexdigest()

        self.assertEqual(run_once("a"), run_once("b"))


if __name__ == "__main__":
    unittest.main()
