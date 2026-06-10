import re
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
CANDIDATES = REPO / "docs" / "references" / "initial-unmanaged-baseline-candidates.md"


class InitialUnmanagedBaselineCandidatesDocTests(unittest.TestCase):
    def test_candidate_artifact_records_observed_unmanaged_smoke_output(self):
        text = CANDIDATES.read_text(encoding="utf-8")

        self.assertIn("Initial Unmanaged Baseline Candidates", text)
        self.assertIn("Issue #15", text)
        self.assertIn("128x128", text)
        self.assertIn("clusters: `300`", text)
        self.assertIn("steps run: `111233`", text)
        self.assertIn("fire size range: `1..16384`", text)
        self.assertIn("orders of magnitude: `4.214`", text)
        self.assertIn("overlap rate: `0.0067`", text)
        self.assertIn("gate status: `pass`", text)

    def test_candidate_artifact_names_provisional_first_pass_pf_settings(self):
        text = CANDIDATES.read_text(encoding="utf-8")

        self.assertIn("p: `0.01`", text)
        self.assertIn("f: `0.000001`", text)
        self.assertIn("f/p: `0.0001`", text)
        self.assertIn("first-pass candidate", text.lower())
        self.assertIn("sweep", text.lower())

    def test_candidate_artifact_records_minimum_credible_first_binding_settings(self):
        text = CANDIDATES.read_text(encoding="utf-8")

        for phrase in [
            "grid: `128x128`",
            "warmup: `10000` steps",
            "closed-cluster target: `300`",
            "smoke-gate minimum: `50` closed clusters",
            "max steps: `200000`",
            "cap by closed-cluster target first",
        ]:
            self.assertIn(phrase, text)

    def test_candidate_artifact_keeps_final_science_and_final_constants_out_of_scope(self):
        text = CANDIDATES.read_text(encoding="utf-8")
        command_blocks = "\n".join(re.findall(r"```(?:bash|text|yaml)?\n(.*?)```", text, flags=re.DOTALL)).lower()

        self.assertIn("does not freeze final arena constants", text.lower())
        self.assertIn("c0.2 science conclusions are out of scope", text.lower())
        self.assertIn("not soc proof", text.lower())
        self.assertNotRegex(command_blocks, r"(^|[;&|]\s*)puffer(\s|$)")
        self.assertNotRegex(command_blocks, r"\btrain\b")
        self.assertNotRegex(command_blocks, r"\beval\b")
        self.assertNotRegex(command_blocks, r"raylib|c_render")


if __name__ == "__main__":
    unittest.main()
