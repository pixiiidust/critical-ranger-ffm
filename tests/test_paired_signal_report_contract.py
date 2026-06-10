import csv
import json
import tempfile
import unittest
from pathlib import Path

from critical_ranger_ffm.reporting.paired_signal_report import (
    PAIRED_SIGNAL_CSV_COLUMNS,
    VALID_SIGNAL_VERDICTS,
    PairedSignalConfig,
    PairedSignalReport,
    build_fixture_signal_rows,
    evaluate_paired_signal_report,
    load_paired_signal_rows,
    write_paired_signal_artifacts,
)


class PairedSignalReportContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rows_path = self.tmp / "paired_signal.csv"

    def write_rows(self, rows):
        with self.rows_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=PAIRED_SIGNAL_CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        return self.rows_path

    def test_paired_csv_schema_requires_pair_matching_outcome_and_protocol_fields(self):
        rows = build_fixture_signal_rows(valid_pairs=2, invalid_pairs=1)
        loaded = load_paired_signal_rows(self.write_rows(rows))

        self.assertEqual(len(loaded), 3)
        expected_columns = {
            "schema_version",
            "run_id",
            "pair_id",
            "seed",
            "episode_id",
            "timestep",
            "treatment_row",
            "treatment_col",
            "treatment_index",
            "control_row",
            "control_col",
            "control_index",
            "ranger_density_trees_7x7",
            "ranger_density_cells_7x7",
            "ranger_density_tercile",
            "control_density_trees_7x7",
            "control_density_cells_7x7",
            "control_density_tercile",
            "match_quality",
            "valid_pair",
            "validity_reason",
            "treatment_burned_cells",
            "control_burned_cells",
            "burned_area_avoided_delta",
            "treatment_living_tree_fraction",
            "control_living_tree_fraction",
            "living_tree_fraction_delta",
            "readout_horizon_steps",
            "config_id",
            "protocol_id",
            "runner_invariant_status",
            "replay_status",
            "evidence_label",
        }
        self.assertEqual(set(PAIRED_SIGNAL_CSV_COLUMNS), expected_columns)
        self.assertEqual(loaded[0]["pair_id"], "pair-000")
        self.assertEqual(loaded[0]["burned_area_avoided_delta"], "4")
        self.assertEqual(loaded[0]["protocol_id"], "switch-point-test-protocol-v1")

        missing = dict(rows[0])
        missing.pop("burned_area_avoided_delta")
        with (self.tmp / "bad.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=[column for column in PAIRED_SIGNAL_CSV_COLUMNS if column != "burned_area_avoided_delta"])
            writer.writeheader()
            writer.writerow(missing)
        with self.assertRaisesRegex(ValueError, "missing required paired signal columns: burned_area_avoided_delta"):
            load_paired_signal_rows(self.tmp / "bad.csv")

    def test_markdown_report_contract_includes_required_signal_metrics_and_smoke_label(self):
        rows = load_paired_signal_rows(self.write_rows(build_fixture_signal_rows(valid_pairs=3, invalid_pairs=1)))
        report = evaluate_paired_signal_report(rows, PairedSignalConfig(target_valid_pairs=100, attempted_pair_cap=150))
        markdown = report.to_markdown()

        required_phrases = [
            "# Paired switch-point signal report",
            "Verdict: `pass_signal`",
            "Evidence label: `signal_smoke_only`",
            "This is a signal/smoke check only",
            "Valid pairs: 3",
            "Attempted pairs: 4",
            "Invalid rate: 25.0%",
            "Mean burned-area avoided: 4.000",
            "Median burned-area avoided: 4.000",
            "Ranger avoided more burned area: 100.0%",
            "Uncertainty interval:",
            "Density-match diagnostics:",
            "Replay status: `ok`",
            "Runner invariant status: `ok`",
            "Seed schedule:",
            "Read-out horizon: 512 steps",
        ]
        for phrase in required_phrases:
            self.assertIn(phrase, markdown)
        self.assertNotIn("ranger efficacy proven", markdown.lower())
        self.assertNotIn("publication-grade", markdown.lower())

    def test_json_summary_uses_fixed_verdict_vocabulary_and_required_fields(self):
        rows = load_paired_signal_rows(self.write_rows(build_fixture_signal_rows(valid_pairs=3, invalid_pairs=0)))
        report = evaluate_paired_signal_report(rows)
        payload = report.to_json_dict()

        self.assertEqual(VALID_SIGNAL_VERDICTS, {"pass_signal", "mixed_signal", "diagnostic_only", "invalid_runner"})
        self.assertIn(payload["verdict"], VALID_SIGNAL_VERDICTS)
        required_keys = {
            "schema_version",
            "run_id",
            "verdict",
            "evidence_label",
            "valid_pairs",
            "attempted_pairs",
            "invalid_pairs",
            "invalid_rate",
            "mean_burned_area_avoided",
            "median_burned_area_avoided",
            "percent_ranger_avoided_more_burned_area",
            "uncertainty_interval",
            "density_match_diagnostics",
            "replay_status",
            "runner_invariant_status",
            "seed_schedule",
            "readout_horizon_steps",
            "config_id",
            "protocol_id",
        }
        self.assertEqual(set(payload), required_keys)
        json.dumps(payload)

    def test_invalid_rate_above_twenty_five_percent_is_diagnostic_only_not_efficacy(self):
        rows = load_paired_signal_rows(self.write_rows(build_fixture_signal_rows(valid_pairs=2, invalid_pairs=1)))
        report = evaluate_paired_signal_report(rows)

        self.assertEqual(report.verdict, "diagnostic_only")
        self.assertGreater(report.invalid_rate, 0.25)
        self.assertIn("invalid-pair rate exceeds 25%", report.notes)
        self.assertEqual(report.evidence_label, "signal_smoke_only")

    def test_replay_or_invariant_invalid_status_maps_to_invalid_runner(self):
        rows = build_fixture_signal_rows(valid_pairs=3, invalid_pairs=0)
        rows[1]["replay_status"] = "mismatch"
        rows[2]["runner_invariant_status"] = "grid_mismatch"
        report = evaluate_paired_signal_report(load_paired_signal_rows(self.write_rows(rows)))

        self.assertEqual(report.verdict, "invalid_runner")
        self.assertIn("replay/invariant failure", report.notes)
        self.assertEqual(report.to_json_dict()["verdict"], "invalid_runner")

    def test_signal_artifact_writer_outputs_paired_csv_markdown_and_json_from_fixtures_only(self):
        output = self.tmp / "out"
        report = PairedSignalReport.from_fixture_rows(build_fixture_signal_rows(valid_pairs=3, invalid_pairs=0))
        artifacts = write_paired_signal_artifacts(report, output)

        self.assertEqual(set(artifacts), {"csv", "markdown", "json"})
        for path in artifacts.values():
            self.assertTrue(path.exists(), path)
        self.assertEqual(load_paired_signal_rows(artifacts["csv"])[0]["evidence_label"], "signal_smoke_only")
        self.assertIn("signal/smoke check only", artifacts["markdown"].read_text(encoding="utf-8"))
        self.assertIn(json.loads(artifacts["json"].read_text(encoding="utf-8"))["verdict"], VALID_SIGNAL_VERDICTS)


if __name__ == "__main__":
    unittest.main()
