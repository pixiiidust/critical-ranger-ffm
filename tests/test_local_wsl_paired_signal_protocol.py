import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PROTOCOL = REPO / "docs" / "references" / "local-wsl-paired-signal-check-protocol.md"


class LocalWslPairedSignalProtocolTests(unittest.TestCase):
    def test_protocol_names_reviewed_real_sample_provider_command(self):
        text = PROTOCOL.read_text(encoding="utf-8")

        required_phrases = [
            "Current command status: `real_sample_provider_ready_for_review`",
            "The reviewed provider callable is `critical_ranger_ffm.reporting.local_wsl_sample_provider:build_local_wsl_switch_point_samples`.",
            "fixture artifacts do not count as #38 evidence",
            "must produce paired CSV, Markdown report, and JSON summary from one invocation",
            "`python3 -m critical_ranger_ffm.reporting.local_wsl_paired_signal_check`",
            "target `100` valid pairs with a `150` attempted-pair cap",
            "local WSL/GTX 1070 only",
            "one command at a time",
            "pass_signal",
            "mixed_signal",
            "diagnostic_only",
            "invalid_runner",
            "`>25%` invalid rate means `diagnostic_only`",
            "replay/invariant invalids hard-stop efficacy interpretation",
            "Do not start #39",
        ]
        for phrase in required_phrases:
            self.assertIn(phrase, text)

    def test_protocol_does_not_publish_blocked_runtime_commands(self):
        text = PROTOCOL.read_text(encoding="utf-8")
        fenced_blocks = text.split("```")
        command_blocks = fenced_blocks[1::2]
        forbidden_terms = ["puffer", "train", "eval", "render", "c_render", "raylib"]
        for block in command_blocks:
            lowered = block.lower()
            for term in forbidden_terms:
                self.assertNotIn(term, lowered)


if __name__ == "__main__":
    unittest.main()
