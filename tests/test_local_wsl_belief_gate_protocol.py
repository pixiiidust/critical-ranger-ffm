from pathlib import Path
import re
import unittest


class LocalWslBeliefGateProtocolTests(unittest.TestCase):
    def setUp(self):
        self.path = Path("docs/references/local-wsl-belief-gate-protocol.md")

    def test_protocol_documents_dedicated_local_wsl_command_and_nonclaims(self):
        text = self.path.read_text(encoding="utf-8")

        required = [
            "Current command status: `belief_gate_command_ready_for_local_wsl_review`",
            "python3 -m critical_ranger_ffm.reporting.local_wsl_belief_gate_check",
            "--target-valid-pairs 500",
            "--attempted-pair-cap 750",
            "--min-independent-seeds 50",
            "--max-valid-pairs-per-seed 10",
            "--max-seed-share 0.05",
            "--readout-horizon-steps 512",
            "belief_gate_report.md",
            "belief_gate_summary.json",
            "paired_signal.csv",
            "pass_belief_gate",
            "mixed_belief_gate",
            "diagnostic_only",
            "invalid_runner",
            "provisional ranger-efficacy belief only",
            "fixture UI is not evidence",
            "not final criticality",
            "not SOC control",
            "not publication-grade science",
            "one command at a time",
        ]
        for phrase in required:
            self.assertIn(phrase, text)

    def test_protocol_fenced_commands_do_not_include_blocked_vps_runtime_words(self):
        text = self.path.read_text(encoding="utf-8")
        commands = "\n".join(re.findall(r"```bash\n(.*?)\n```", text, flags=re.DOTALL))
        forbidden = ["puffer", "train", "eval", "raylib", "c_render"]
        for word in forbidden:
            self.assertNotIn(word, commands.lower())


if __name__ == "__main__":
    unittest.main()
