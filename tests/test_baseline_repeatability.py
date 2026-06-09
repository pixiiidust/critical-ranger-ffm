import csv
import json
import tempfile
import unittest
from pathlib import Path

from critical_ranger_ffm.baseline.repeatability import (
    DEFAULT_REPEATABILITY_THRESHOLDS,
    compare_arena_constants,
    compute_seed_summary,
    evaluate_repeatability,
    load_ini_config,
    run_repeatability_sweep,
)
from critical_ranger_ffm.reporting.report_fire_sizes import fit_slope


REPO = Path(__file__).resolve().parents[1]
BASELINE_CONFIG = REPO / "configs" / "ffm_baseline_smoke.ini"
FROZEN_ARENA = REPO / "configs" / "ffm_arena.frozen.ini"
DEMO_SOURCE = REPO / "demos" / "ffm_baseline_smoke.c"


class BaselineRepeatabilityTests(unittest.TestCase):
    def test_frozen_arena_config_pins_shared_constants_and_thresholds(self):
        frozen = load_ini_config(FROZEN_ARENA)
        self.assertEqual(frozen["grid_width"], "128")
        self.assertEqual(frozen["grid_height"], "128")
        self.assertEqual(frozen["connectivity"], "4")
        self.assertEqual(frozen["p"], "0.01")
        self.assertEqual(frozen["f"], "0.000001")
        self.assertEqual(frozen["warmup_steps"], "10000")
        self.assertEqual(frozen["cluster_target"], "2000")
        self.assertIn("repeatability_density_max_range", frozen)
        self.assertIn("repeatability_slope_max_range", frozen)

    def test_baseline_config_matches_frozen_arena_constants(self):
        mismatches = compare_arena_constants(FROZEN_ARENA, BASELINE_CONFIG)
        self.assertEqual(mismatches, [])

    def test_arena_guard_catches_changed_agent_comparison_constants(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir) / "agent.ini"
            text = FROZEN_ARENA.read_text(encoding="utf-8").replace("p=0.01", "p=0.02")
            tmp.write_text(text, encoding="utf-8")
            mismatches = compare_arena_constants(FROZEN_ARENA, tmp)
        self.assertTrue(any("p:" in mismatch for mismatch in mismatches), mismatches)

    def test_compute_seed_summary_uses_canonical_part_b_slope_function(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "clusters.csv"
            sizes = [1, 2, 4, 8, 16, 32, 64]
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
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
                        "pair_id",
                        "source",
                        "notes",
                    ],
                )
                writer.writeheader()
                for index, size in enumerate(sizes, start=1):
                    writer.writerow(
                        {
                            "schema_version": "1",
                            "run_id": "fixture",
                            "mode": "baseline",
                            "seed": "1",
                            "episode_id": "0",
                            "step": str(index),
                            "event_id": str(index),
                            "cluster_id": "1",
                            "fire_size": str(size),
                            "grid_width": "128",
                            "grid_height": "128",
                            "p": "0.01",
                            "f": "0.000001",
                            "global_tree_density": "0.6",
                            "quiet_window_component_count": "1",
                            "pair_id": "",
                            "source": "env",
                            "notes": "",
                        }
                    )
            summary_json = Path(tmp_dir) / "summary.json"
            summary_json.write_text(
                json.dumps(
                    {
                        "critical_density_mean": 0.6,
                        "multi_component_window_rate": 0.0,
                        "steps_run": 100,
                        "cluster_count": len(sizes),
                        "orders_of_magnitude": 1.806,
                        "measurement_grid_gate": "pass",
                        "sample_size_gate": "pass",
                        "size_range_gate": "pass",
                        "overlap_gate": "pass",
                        "critical_density_gate": "pass",
                        "heavy_tail_gate": "pass",
                    }
                ),
                encoding="utf-8",
            )
            summary = compute_seed_summary(csv_path, summary_json)
        self.assertEqual(summary["fitted_slope"], fit_slope(sizes))

    def test_repeatability_gate_has_hard_thresholds_and_can_fail(self):
        seed_summaries = [
            {"seed": 1, "critical_density_mean": 0.55, "fitted_slope": -0.10, "orders_of_magnitude": 2.0, "multi_component_window_rate": 0.0, "cluster_count": 2000, "heavy_tail_gate": "pass"},
            {"seed": 2, "critical_density_mean": 0.70, "fitted_slope": -0.40, "orders_of_magnitude": 2.0, "multi_component_window_rate": 0.0, "cluster_count": 2000, "heavy_tail_gate": "pass"},
        ]
        result = evaluate_repeatability(seed_summaries, {"density_max_range": 0.05, "slope_max_range": 0.10})
        self.assertEqual(result["repeatability_gate"], "fail")
        self.assertFalse(result["density_repeatability_pass"])
        self.assertFalse(result["slope_repeatability_pass"])

    def test_fast_repeatability_sweep_runs_multiple_seeds_and_writes_summary(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = run_repeatability_sweep(
                demo_source=DEMO_SOURCE,
                config_path=BASELINE_CONFIG,
                out_dir=Path(tmp_dir),
                seeds=[101, 102],
                overrides={
                    "grid_width": "32",
                    "grid_height": "32",
                    "min_gate_grid_size": "32",
                    "warmup_steps": "20",
                    "cluster_target": "5",
                    "max_steps": "50000",
                    "p": "0.05",
                    "f": "0.0001",
                },
                thresholds=DEFAULT_REPEATABILITY_THRESHOLDS,
            )
        self.assertEqual(len(result["seeds"]), 2)
        self.assertIn(result["repeatability_gate"], ["pass", "fail"])
        self.assertIn("density_range", result)
        self.assertIn("slope_range", result)


if __name__ == "__main__":
    unittest.main()
