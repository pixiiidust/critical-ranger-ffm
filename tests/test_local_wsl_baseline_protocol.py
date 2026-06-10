import re
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PROTOCOL = REPO / "docs" / "references" / "local-wsl-unmanaged-baseline-protocol.md"


class LocalWslBaselineProtocolDocTests(unittest.TestCase):
    def test_protocol_exists_and_names_hitl_scope(self):
        text = PROTOCOL.read_text(encoding="utf-8")

        self.assertIn("Local WSL Unmanaged Baseline Protocol", text)
        self.assertIn("HITL", text)
        self.assertIn("one command at a time", text.lower())
        self.assertIn("external PowerShell", text)
        self.assertIn("wsl --cd", text)

    def test_protocol_separates_debug_from_measurement(self):
        text = PROTOCOL.read_text(encoding="utf-8")

        self.assertRegex(text, r"32x32")
        self.assertRegex(text, r"128x128\+")
        self.assertIn("debug grid is not soc evidence", text.lower())
        self.assertIn("measurement_grid_gate", text)

    def test_protocol_keeps_gpu_puffer_and_render_out_of_scope(self):
        text = PROTOCOL.read_text(encoding="utf-8")
        command_blocks = re.findall(r"```(?:bash|powershell|text)?\n(.*?)```", text, flags=re.DOTALL)
        commands = "\n".join(command_blocks).lower()

        self.assertIn("do not run puffer/gpu commands on the vps", text.lower())
        self.assertNotRegex(commands, r"(^|[;&|]\s*)puffer(\s|$)")
        self.assertNotRegex(commands, r"\btrain\b")
        self.assertNotRegex(commands, r"\beval\b")
        self.assertNotRegex(commands, r"raylib|c_render")

    def test_protocol_defines_status_summary_outcomes(self):
        text = PROTOCOL.read_text(encoding="utf-8")

        for status in ["pass", "tune p/f", "run longer", "fix environment bug"]:
            self.assertIn(status, text.lower())
        self.assertIn("do not claim final science", text.lower())

    def test_jamie_pasted_result_is_documented_without_final_science_claim(self):
        text = PROTOCOL.read_text(encoding="utf-8")

        self.assertIn("Jamie-pasted local WSL result", text)
        self.assertIn("Baseline status for Issue #14: `pass`", text)
        self.assertIn("reports/local-wsl-issue-14-debug/clusters.csv", text)
        self.assertIn("reports/local-wsl-issue-14-measurement/summary.json", text)
        self.assertIn("This result is enough to complete the local WSL protocol slice", text)
        self.assertIn("It does not claim final science", text)


if __name__ == "__main__":
    unittest.main()
