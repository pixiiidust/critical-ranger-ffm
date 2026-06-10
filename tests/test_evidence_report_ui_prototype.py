import tempfile
import unittest
from pathlib import Path

from critical_ranger_ffm.reporting.evidence_report_ui import (
    render_fixture_evidence_report_ui,
    write_fixture_evidence_report_ui,
)


class EvidenceReportUiPrototypeTests(unittest.TestCase):
    def test_fixture_ui_is_labeled_non_evidence_and_uses_report_contract_fields(self):
        html = render_fixture_evidence_report_ui()

        required_phrases = [
            "Critical Ranger FFM evidence report prototype",
            "FIXTURE SAMPLE — NOT EVIDENCE",
            "This browser prototype uses generated fixture/sample data only",
            "dark simulation lab",
            "Seed/config controls",
            "Large grid viewport",
            "Side-by-side signal and report panels",
            "Animation toggle",
            "signal_smoke_only",
            "valid_pairs",
            "attempted_pairs",
            "invalid_rate",
            "mean_burned_area_avoided",
            "density_match_diagnostics",
            "runner_invariant_status",
            "replay_status",
            "readout_horizon_steps",
            "No real experiment output is loaded or required",
        ]
        for phrase in required_phrases:
            self.assertIn(phrase, html)

        forbidden_claims = [
            "ranger efficacy proven",
            "soc proof",
            "publication-grade",
            "policy-quality",
            "belief evidence",
        ]
        lowered = html.lower()
        for claim in forbidden_claims:
            self.assertNotIn(claim, lowered)

    def test_fixture_ui_is_static_browser_safe_and_has_interactive_controls(self):
        html = render_fixture_evidence_report_ui()

        self.assertIn("<button", html)
        self.assertIn("data-seed-button", html)
        self.assertIn("id=\"animation-toggle\"", html)
        self.assertIn("id=\"grid-viewport\"", html)
        self.assertIn("id=\"report-panel\"", html)
        self.assertIn("id=\"signal-panel\"", html)
        self.assertIn("function renderGrid", html)
        self.assertIn("const fixtureRows", html)
        self.assertIn("const fixtureSummary", html)
        self.assertNotIn("puffer", html.lower())
        self.assertNotIn("raylib", html.lower())
        self.assertNotIn("c_render", html)
        self.assertNotIn("gpu", html.lower())
        self.assertNotIn("train", html.lower())

    def test_writer_creates_single_static_html_artifact(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = write_fixture_evidence_report_ui(Path(tmp_dir))

            self.assertEqual(output_path.name, "evidence-report-ui.html")
            self.assertTrue(output_path.exists())
            html = output_path.read_text(encoding="utf-8")
            self.assertIn("FIXTURE SAMPLE — NOT EVIDENCE", html)
            self.assertIn("window.CRITICAL_RANGER_FFM_FIXTURE_UI", html)


if __name__ == "__main__":
    unittest.main()
