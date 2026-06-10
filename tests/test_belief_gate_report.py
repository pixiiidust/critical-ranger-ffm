import csv
import json
import tempfile
import unittest
from pathlib import Path

from critical_ranger_ffm.reporting.belief_gate_report import (
    EVIDENCE_LABEL_PROVISIONAL_BELIEF_GATE,
    VALID_BELIEF_GATE_VERDICTS,
    BeliefGateConfig,
    evaluate_belief_gate_report,
    write_belief_gate_artifacts,
)
from critical_ranger_ffm.reporting.paired_signal_report import (
    PAIRED_SIGNAL_CSV_COLUMNS,
    build_fixture_signal_rows,
    load_paired_signal_rows,
)


class BeliefGateReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def write_rows(self, rows):
        rows_path = self.tmp / "paired_signal.csv"
        with rows_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=PAIRED_SIGNAL_CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        return load_paired_signal_rows(rows_path)

    def belief_rows(self, valid_pairs=500, seed_count=50, delta=4, attempted_extra_invalid=0):
        rows = build_fixture_signal_rows(valid_pairs=valid_pairs, invalid_pairs=attempted_extra_invalid)
        for index, row in enumerate(rows):
            row["run_id"] = "issue49-local-wsl-belief-gate"
            row["config_id"] = "local-wsl-belief-gate-v1"
            row["seed"] = str(50_000 + (index % seed_count))
            row["episode_id"] = f"belief-seed-{row['seed']}"
            if row["valid_pair"] == "true":
                control = 20 + (index % 7)
                treatment = control - delta
                row["control_burned_cells"] = str(control)
                row["treatment_burned_cells"] = str(treatment)
                row["burned_area_avoided_delta"] = str(delta)
        return rows

    def test_fixed_vocabulary_and_passing_thresholds_classify_only_provisional_belief(self):
        report = evaluate_belief_gate_report(self.write_rows(self.belief_rows()))
        payload = report.to_json_dict()
        markdown = report.to_markdown()

        self.assertEqual(VALID_BELIEF_GATE_VERDICTS, {"pass_belief_gate", "mixed_belief_gate", "diagnostic_only", "invalid_runner"})
        self.assertEqual(report.verdict, "pass_belief_gate")
        self.assertEqual(report.evidence_label, EVIDENCE_LABEL_PROVISIONAL_BELIEF_GATE)
        self.assertEqual(report.valid_pairs, 500)
        self.assertEqual(report.seed_count, 50)
        self.assertEqual(report.max_valid_pairs_per_seed, 10)
        self.assertLessEqual(report.max_seed_share, 0.05)
        self.assertIn("seed_stratified_burned_area_avoided", payload)
        self.assertIn("uncertainty_interval", payload)
        self.assertIn("density_match_diagnostics", payload)
        self.assertIn("Passing this gate supports provisional ranger-efficacy belief only", markdown)
        self.assertNotIn("final criticality", markdown.lower().replace("not final criticality", ""))
        json.dumps(payload)

    def test_threshold_failures_are_diagnostic_not_belief_evidence(self):
        too_few_seeds = evaluate_belief_gate_report(self.write_rows(self.belief_rows(seed_count=49)))
        self.assertEqual(too_few_seeds.verdict, "diagnostic_only")
        self.assertIn("independent seed count below threshold", too_few_seeds.notes)

        one_seed_dominates = self.belief_rows(seed_count=50)
        for row in one_seed_dominates[:26]:
            row["seed"] = "999999"
        dominated = evaluate_belief_gate_report(self.write_rows(one_seed_dominates))
        self.assertEqual(dominated.verdict, "diagnostic_only")
        self.assertIn("seed contribution exceeds max valid pairs per seed", dominated.notes)
        self.assertIn("seed contribution exceeds max share", dominated.notes)

        too_many_attempts = evaluate_belief_gate_report(self.write_rows(self.belief_rows(attempted_extra_invalid=251)))
        self.assertEqual(too_many_attempts.verdict, "diagnostic_only")
        self.assertIn("attempted pairs exceed cap", too_many_attempts.notes)

    def test_mixed_direction_and_runner_failure_use_belief_gate_vocabulary(self):
        mixed_rows = self.belief_rows(delta=-1)
        mixed = evaluate_belief_gate_report(self.write_rows(mixed_rows))
        self.assertEqual(mixed.verdict, "mixed_belief_gate")

        invalid_rows = self.belief_rows()
        invalid_rows[0]["replay_status"] = "mismatch"
        invalid = evaluate_belief_gate_report(self.write_rows(invalid_rows))
        self.assertEqual(invalid.verdict, "invalid_runner")
        self.assertIn("replay/invariant failure", invalid.notes)

    def test_writer_outputs_paired_csv_belief_markdown_and_json_summary(self):
        rows = self.write_rows(self.belief_rows())
        artifacts = write_belief_gate_artifacts(rows, self.tmp / "out")

        self.assertEqual(set(artifacts), {"csv", "markdown", "json"})
        self.assertEqual(artifacts["csv"].name, "paired_signal.csv")
        self.assertEqual(artifacts["markdown"].name, "belief_gate_report.md")
        self.assertEqual(artifacts["json"].name, "belief_gate_summary.json")
        payload = json.loads(artifacts["json"].read_text(encoding="utf-8"))
        self.assertEqual(payload["verdict"], "pass_belief_gate")
        self.assertEqual(payload["evidence_label"], EVIDENCE_LABEL_PROVISIONAL_BELIEF_GATE)
        self.assertIn("seed-stratified burned-area avoided", artifacts["markdown"].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
