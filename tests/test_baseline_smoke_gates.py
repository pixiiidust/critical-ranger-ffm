import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from critical_ranger_ffm.reporting.report_fire_sizes import REQUIRED_CLUSTER_COLUMNS


class BaselineSmokeGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.clusters = self.tmp / "clusters.csv"
        self.summary = self.tmp / "summary.json"

    def write_clusters(self, sizes, overlap_every=0):
        with self.clusters.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=REQUIRED_CLUSTER_COLUMNS)
            writer.writeheader()
            for index, size in enumerate(sizes, start=1):
                overlap = overlap_every and index % overlap_every == 0
                writer.writerow(
                    {
                        "schema_version": "1",
                        "run_id": "gate-fixture",
                        "mode": "baseline",
                        "seed": "13",
                        "episode_id": "0",
                        "step": str(index * 10),
                        "event_id": str(index),
                        "cluster_id": str(index),
                        "fire_size": str(size),
                        "grid_width": "128",
                        "grid_height": "128",
                        "p": "0.01",
                        "f": "0.000001",
                        "global_tree_density": "0.55",
                        "quiet_window_component_count": "2" if overlap else "1",
                        "overlap_signal": "multi_component" if overlap else "single_component",
                        "pair_id": "",
                        "source": "unit-test",
                        "notes": "",
                    }
                )
        self.summary.write_text(
            json.dumps(
                {
                    "run_id": "gate-fixture",
                    "seed": 13,
                    "steps_run": len(sizes) * 10,
                    "closed_cluster_count": len(sizes),
                    "overlap_rate": (len([i for i in range(1, len(sizes) + 1) if overlap_every and i % overlap_every == 0]) / len(sizes))
                    if sizes
                    else 0.0,
                }
            ),
            encoding="utf-8",
        )

    def test_insufficient_sample_fails_and_recommends_running_longer(self):
        from critical_ranger_ffm.reporting.baseline_smoke_gates import evaluate_baseline_gates

        self.write_clusters([1, 2, 4])

        result = evaluate_baseline_gates(self.clusters, self.summary)

        self.assertEqual(result.status, "fail")
        self.assertTrue(any("too few closed clusters" in message for message in result.messages), result.messages)
        self.assertIn("run longer", result.recommendation)

    def test_narrow_tail_warns_and_recommends_tuning_p_or_f(self):
        from critical_ranger_ffm.reporting.baseline_smoke_gates import BaselineGateConfig, evaluate_baseline_gates

        self.write_clusters([4, 4, 5, 5, 6, 6])

        result = evaluate_baseline_gates(
            self.clusters,
            self.summary,
            BaselineGateConfig(min_closed_clusters=4, min_orders_of_magnitude=1.0, min_tail_fire_size=32),
        )

        self.assertIn(result.status, ["fail", "warn"])
        self.assertTrue(any("too-narrow fire-size range" in message for message in result.messages), result.messages)
        self.assertTrue(any("unpopulated tail" in message for message in result.messages), result.messages)
        self.assertRegex(result.recommendation, r"tune (p|f)")

    def test_common_overlap_warns_and_recommends_tuning_f_or_longer_windows(self):
        from critical_ranger_ffm.reporting.baseline_smoke_gates import BaselineGateConfig, evaluate_baseline_gates

        self.write_clusters([1, 2, 4, 8, 16, 32, 64, 128], overlap_every=2)

        result = evaluate_baseline_gates(
            self.clusters,
            self.summary,
            BaselineGateConfig(min_closed_clusters=4, min_orders_of_magnitude=1.0, max_overlap_rate=0.10),
        )

        self.assertIn(result.status, ["fail", "warn"])
        self.assertTrue(any("overlap is common" in message for message in result.messages), result.messages)
        self.assertRegex(result.recommendation, r"tune f|quiet window")

    def test_ready_run_passes_without_c0_1_slope_or_repeatability_gates(self):
        from critical_ranger_ffm.reporting.baseline_smoke_gates import BaselineGateConfig, evaluate_baseline_gates

        self.write_clusters([1, 2, 4, 8, 16, 32, 64, 128], overlap_every=0)

        result = evaluate_baseline_gates(
            self.clusters,
            self.summary,
            BaselineGateConfig(min_closed_clusters=4, min_orders_of_magnitude=1.0, min_tail_fire_size=32),
        )

        self.assertEqual(result.status, "pass")
        self.assertIn("move to measurement runs", result.recommendation)
        output = "\n".join([result.status, result.recommendation, *result.messages]).lower()
        self.assertNotIn("slope", output)
        self.assertNotIn("repeatability", output)

    def test_cli_outputs_json_and_nonzero_on_failed_gate(self):
        self.write_clusters([1, 2, 4])

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "critical_ranger_ffm.reporting.baseline_smoke_gates",
                "--clusters",
                str(self.clusters),
                "--summary-json",
                str(self.summary),
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 1, completed.stderr + completed.stdout)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["status"], "fail")
        self.assertIn("recommendation", payload)
        self.assertTrue(payload["messages"])


if __name__ == "__main__":
    unittest.main()
