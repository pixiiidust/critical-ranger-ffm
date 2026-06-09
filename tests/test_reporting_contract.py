import csv
import tempfile
import unittest
from pathlib import Path

from critical_ranger_ffm.reporting.report_fire_sizes import (
    REQUIRED_CLUSTER_COLUMNS,
    REQUIRED_INTERVENTION_COLUMNS,
    ReportingConfig,
    load_cluster_rows,
    load_intervention_rows,
    validate_pairing_contract,
)


class ReportingContractTests(unittest.TestCase):
    def write_csv(self, rows):
        path = Path(tempfile.mkdtemp()) / "rows.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        return path

    def cluster_row(self, **overrides):
        row = {column: "" for column in REQUIRED_CLUSTER_COLUMNS}
        row.update(
            {
                "schema_version": "1",
                "run_id": "fixture-baseline",
                "mode": "baseline",
                "seed": "101",
                "episode_id": "0",
                "step": "100",
                "event_id": "1",
                "cluster_id": "1",
                "fire_size": "3",
                "grid_width": "128",
                "grid_height": "128",
                "p": "0.01",
                "f": "0.000001",
                "global_tree_density": "0.55",
                "quiet_window_component_count": "1",
                "overlap_signal": "single_component",
                "source": "synthetic",
            }
        )
        row.update(overrides)
        return row

    def intervention_row(self, **overrides):
        row = {column: "" for column in REQUIRED_INTERVENTION_COLUMNS}
        row.update(
            {
                "schema_version": "1",
                "pair_id": "pair-001",
                "run_id": "fixture-ranger",
                "mode": "ranger_intervention",
                "seed": "202",
                "episode_id": "0",
                "intervention_step": "1000",
                "action_row": "4",
                "action_col": "5",
                "selected_cell_state": "tree",
                "effective_intervention": "true",
                "local_fuel_density": "0.66",
                "density_bucket": "mid",
                "matched_control_for_pair_id": "pair-001",
                "post_intervention_seed": "999",
                "downstream_window_steps": "5000",
                "source": "synthetic",
            }
        )
        row.update(overrides)
        return row

    def test_cluster_csv_requires_contract_columns(self):
        path = self.write_csv([self.cluster_row()])
        rows = load_cluster_rows(path)
        self.assertEqual(rows[0]["mode"], "baseline")

        missing = self.cluster_row()
        missing.pop("fire_size")
        bad_path = self.write_csv([missing])
        with self.assertRaisesRegex(ValueError, "missing required cluster columns: fire_size"):
            load_cluster_rows(bad_path)

    def test_unknown_cluster_mode_fails_clearly(self):
        path = self.write_csv([self.cluster_row(mode="pure_random_control")])
        with self.assertRaisesRegex(ValueError, "unknown cluster mode"):
            load_cluster_rows(path)

    def test_intervention_pairs_warn_when_density_buckets_do_not_match(self):
        rows = [
            self.intervention_row(mode="ranger_intervention", density_bucket="high"),
            self.intervention_row(
                mode="density_matched_control",
                run_id="fixture-control",
                action_row="8",
                action_col="9",
                density_bucket="low",
            ),
        ]
        warnings = validate_pairing_contract(rows, ReportingConfig())
        self.assertTrue(
            any("density bucket mismatch" in warning for warning in warnings),
            warnings,
        )

    def test_non_effective_interventions_are_warned_and_excluded_by_default(self):
        rows = [
            self.intervention_row(mode="ranger_intervention", effective_intervention="false", selected_cell_state="empty"),
            self.intervention_row(
                mode="density_matched_control",
                run_id="fixture-control",
                action_row="8",
                action_col="9",
                effective_intervention="true",
                selected_cell_state="tree",
            ),
        ]
        warnings = validate_pairing_contract(rows, ReportingConfig(filter_non_effective_interventions=True))
        self.assertTrue(
            any("non-effective intervention excluded" in warning for warning in warnings),
            warnings,
        )

    def test_effective_intervention_semantics_are_enforced(self):
        rows = [self.intervention_row(effective_intervention="true", selected_cell_state="burning")]
        with self.assertRaisesRegex(ValueError, "effective_intervention=true requires selected_cell_state=tree"):
            validate_pairing_contract(rows, ReportingConfig())


if __name__ == "__main__":
    unittest.main()
