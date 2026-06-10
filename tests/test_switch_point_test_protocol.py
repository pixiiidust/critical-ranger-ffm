import re
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PROTOCOL = REPO / "docs" / "references" / "switch-point-test-protocol.md"


class SwitchPointTestProtocolDocTests(unittest.TestCase):
    def test_protocol_names_the_paired_counterfactual_comparison(self):
        text = PROTOCOL.read_text(encoding="utf-8")
        lowered = text.lower()

        self.assertIn("Switch-Point Test Protocol", text)
        self.assertIn("Issue #18", text)
        self.assertIn("ranger-chosen intervention", lowered)
        self.assertIn("density-matched control", lowered)
        self.assertIn("same timestep", lowered)
        self.assertIn("same pre-intervention grid", lowered)

    def test_protocol_requires_shared_rng_after_intervention(self):
        text = PROTOCOL.read_text(encoding="utf-8").lower()

        for phrase in [
            "shared seed",
            "post-intervention lightning/regrowth sequence",
            "same sampled lightning cells",
            "same regrowth draws",
        ]:
            self.assertIn(phrase, text)

    def test_protocol_freezes_policy_after_the_intervention(self):
        text = PROTOCOL.read_text(encoding="utf-8").lower()

        self.assertIn("policy is frozen after the intervention", text)
        self.assertIn("read-out window", text)
        self.assertIn("no further learning", text)
        self.assertIn("no adaptive second intervention", text)

    def test_protocol_sets_sample_count_and_belief_thresholds(self):
        text = PROTOCOL.read_text(encoding="utf-8").lower()

        self.assertIn("100 paired samples", text)
        self.assertIn("signal check only", text)
        self.assertIn("several hundred", text)
        self.assertIn("many seeds", text)
        self.assertIn("before belief", text)

    def test_protocol_avoids_noisy_fire_size_overfit_and_final_science_claims(self):
        text = PROTOCOL.read_text(encoding="utf-8")
        lowered = text.lower()
        command_blocks = "\n".join(
            re.findall(r"```(?:bash|text|yaml)?\n(.*?)```", text, flags=re.DOTALL)
        ).lower()

        self.assertIn("do not optimize on a single noisy fire-size metric", lowered)
        self.assertIn("publication-grade soc proof is out of scope", lowered)
        self.assertIn("policy-quality claim is out of scope", lowered)
        self.assertNotRegex(lowered, r"\bproves\s+soc\b")
        self.assertNotRegex(lowered, r"publication-grade\s+proof")
        self.assertNotRegex(command_blocks, r"(^|[;&|]\s*)puffer(\s|$)")
        self.assertNotRegex(command_blocks, r"\btrain\b|\beval\b|raylib|c_render")

    def test_protocol_requires_human_approval_before_implementation_issues(self):
        text = PROTOCOL.read_text(encoding="utf-8").lower()

        self.assertIn("do not create implementation issues", text)
        self.assertIn("until jamie approves this protocol", text)
        self.assertIn("protocol/planning only", text)


if __name__ == "__main__":
    unittest.main()
