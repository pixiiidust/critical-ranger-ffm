import csv
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from critical_ranger_ffm.reporting.report_fire_sizes import REQUIRED_CLUSTER_COLUMNS, load_cluster_rows


REPO = Path(__file__).resolve().parents[1]
DEMO_SOURCE = REPO / "demos" / "ffm_unmanaged_demo.c"
ENV_SOURCE = REPO / "src" / "critical_ranger_ffm" / "ffm_unmanaged.c"
INCLUDE = REPO / "src" / "critical_ranger_ffm"
CONFIG = REPO / "configs" / "ffm_unmanaged_demo.ini"


class FfmUnmanagedDemoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.binary = self.tmp / "ffm_unmanaged_demo"

    def compile_demo(self):
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
                str(DEMO_SOURCE),
                str(ENV_SOURCE),
                "-o",
                str(self.binary),
            ],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)

    def run_demo(self, *args, expect_ok=True):
        self.compile_demo()
        completed = subprocess.run(
            [str(self.binary), *args],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        if expect_ok:
            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        else:
            self.assertNotEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        return completed

    def test_default_config_is_cpu_safe_small_debug_smoke(self):
        text = CONFIG.read_text(encoding="utf-8")
        self.assertIn("grid_width=8", text)
        self.assertIn("grid_height=8", text)
        self.assertIn("seed=20260610", text)
        self.assertIn("p=0.05", text)
        self.assertIn("f=0.02", text)
        self.assertIn("episode_step_cap=12", text)
        self.assertIn("smoke_step_cap=6", text)
        self.assertIn("debug_every=2", text)
        self.assertNotIn("puffer", text.lower())
        self.assertNotIn("gpu", text.lower())

    def test_config_drives_demo_output_shape_and_state_counters(self):
        completed = self.run_demo(
            "--config", str(CONFIG),
            "--grid-width", "4",
            "--grid-height", "3",
            "--seed", "99",
            "--p", "0.25",
            "--f", "0.125",
            "--episode-step-cap", "7",
            "--smoke-step-cap", "3",
            "--debug-every", "1",
        )
        stdout = completed.stdout
        self.assertIn("Critical Ranger FFM unmanaged demo smoke", stdout)
        self.assertIn("seed=99 grid=4x3 p=0.25 f=0.125 episode_step_cap=7 smoke_step_cap=3", stdout)
        self.assertRegex(stdout, r"step=0 empty=\d+ tree=\d+ burning=\d+")
        self.assertRegex(stdout, r"step=1 empty=\d+ tree=\d+ burning=\d+ active_before=\d+ active_after=\d+ regrowths=\d+ lightning=\d+ truncated=0")
        self.assertRegex(stdout, r"step=3 empty=\d+ tree=\d+ burning=\d+ active_before=\d+ active_after=\d+ regrowths=\d+ lightning=\d+ truncated=0")
        self.assertRegex(stdout, r"result=pass steps_run=3 truncated=0 empty=\d+ tree=\d+ burning=\d+ total_cells=12")

    def test_same_seed_and_config_produce_identical_demo_output(self):
        args = (
            "--config", str(CONFIG),
            "--grid-width", "5",
            "--grid-height", "5",
            "--seed", "4242",
            "--p", "0.1",
            "--f", "0.05",
            "--episode-step-cap", "10",
            "--smoke-step-cap", "4",
            "--debug-every", "2",
        )
        first = self.run_demo(*args).stdout
        second = self.run_demo(*args).stdout
        self.assertEqual(first, second)
        step_lines = [line for line in first.splitlines() if re.match(r"step=", line)]
        self.assertGreaterEqual(len(step_lines), 3)

    def test_cluster_csv_and_summary_contract_are_stable_and_parseable(self):
        out_csv = self.tmp / "clusters.csv"
        summary_json = self.tmp / "summary.json"
        completed = self.run_demo(
            "--config", str(CONFIG),
            "--run-id", "issue-12-contract",
            "--clusters-csv", str(out_csv),
            "--summary-json", str(summary_json),
            "--grid-width", "6",
            "--grid-height", "6",
            "--seed", "1212",
            "--p", "0.0",
            "--f", "0.2",
            "--initial-tree-density", "0.8",
            "--episode-step-cap", "12",
            "--smoke-step-cap", "12",
            "--debug-every", "3",
        )
        self.assertIn(f"clusters_csv={out_csv}", completed.stdout)
        self.assertIn(f"summary_json={summary_json}", completed.stdout)

        self.assertIn("overlap_signal", REQUIRED_CLUSTER_COLUMNS)
        with out_csv.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            self.assertEqual(reader.fieldnames, REQUIRED_CLUSTER_COLUMNS)
        rows = load_cluster_rows(out_csv)
        self.assertGreater(len(rows), 0)
        first = rows[0]
        self.assertEqual(first["run_id"], "issue-12-contract")
        self.assertEqual(first["seed"], "1212")
        self.assertEqual(first["mode"], "baseline")
        self.assertEqual(first["source"], "unmanaged_demo")
        self.assertIn(first["overlap_signal"], ["single_component", "multi_component"])
        self.assertGreaterEqual(int(first["quiet_window_component_count"]), 1)
        self.assertGreaterEqual(float(first["global_tree_density"]), 0.0)
        self.assertLessEqual(float(first["global_tree_density"]), 1.0)

        summary = json.loads(summary_json.read_text(encoding="utf-8"))
        self.assertEqual(summary["run_id"], "issue-12-contract")
        self.assertEqual(summary["seed"], 1212)
        self.assertEqual(summary["grid_width"], 6)
        self.assertEqual(summary["grid_height"], 6)
        self.assertEqual(summary["p"], 0.0)
        self.assertEqual(summary["f"], 0.2)
        self.assertEqual(summary["steps_run"], 12)
        self.assertEqual(summary["closed_cluster_count"], len(rows))
        self.assertGreaterEqual(summary["cluster_size_max"], summary["cluster_size_min"])
        self.assertIn("overlap_rate", summary)
        self.assertIn("overlap_warnings", summary)

    def test_same_seed_replay_writes_identical_cluster_csv_rows(self):
        def run_once(name):
            out_csv = self.tmp / f"{name}.csv"
            summary_json = self.tmp / f"{name}.json"
            self.run_demo(
                "--config", str(CONFIG),
                "--run-id", "deterministic-replay",
                "--clusters-csv", str(out_csv),
                "--summary-json", str(summary_json),
                "--grid-width", "6",
                "--grid-height", "6",
                "--seed", "3434",
                "--p", "0.0",
                "--f", "0.2",
                "--initial-tree-density", "0.8",
                "--episode-step-cap", "12",
                "--smoke-step-cap", "12",
                "--debug-every", "4",
            )
            return out_csv.read_text(encoding="utf-8")

        self.assertEqual(run_once("a"), run_once("b"))

    def test_invalid_config_exits_nonzero_with_clear_error(self):
        bad_config = self.tmp / "bad.ini"
        bad_config.write_text("grid_width=0\ngrid_height=4\np=1.5\n", encoding="utf-8")
        completed = self.run_demo("--config", str(bad_config), expect_ok=False)
        self.assertIn("ERROR:", completed.stderr)
        self.assertIn("invalid unmanaged demo config", completed.stderr)


if __name__ == "__main__":
    unittest.main()
