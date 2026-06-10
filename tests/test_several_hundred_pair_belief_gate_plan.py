import re
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PLAN = REPO / "docs" / "references" / "several-hundred-pair-belief-gate-plan.md"


class SeveralHundredPairBeliefGatePlanDocTests(unittest.TestCase):
    def test_plan_reviews_100_pair_signal_before_scale_up(self):
        text = PLAN.read_text(encoding="utf-8")
        lowered = text.lower()

        self.assertIn("#39", text)
        self.assertIn("#38", text)
        self.assertIn("mixed_signal", text)
        self.assertIn("valid_pairs=100", text)
        self.assertIn("attempted_pairs=100", text)
        self.assertIn("invalid_rate=0.000", text)
        self.assertIn("replay_status=ok", text)
        self.assertIn("runner_invariant_status=ok", text)
        self.assertIn("readout_horizon_steps=512", text)
        for phrase in [
            "invalid rate",
            "density-match diagnostics",
            "replay/invariant status",
            "uncertainty",
            "horizon sensitivity",
        ]:
            self.assertIn(phrase, lowered)

    def test_plan_preserves_locked_belief_gate_thresholds(self):
        text = PLAN.read_text(encoding="utf-8").lower()

        for phrase in [
            "500 valid pairs",
            "at least 50 independent seeds",
            "max 10 valid pairs per seed",
            "no seed over 5%",
            "750 attempted-pair cap",
        ]:
            self.assertIn(phrase, text)

    def test_plan_requires_reporting_outputs_and_seed_stratification(self):
        text = PLAN.read_text(encoding="utf-8").lower()

        for phrase in [
            "aggregate burned-area avoided",
            "seed-stratified burned-area avoided",
            "invalid-rate reporting",
            "density-match diagnostics",
            "uncertainty reporting",
        ]:
            self.assertIn(phrase, text)

    def test_plan_keeps_scale_up_blocked_and_avoids_final_claims_or_vps_runtime_commands(self):
        text = PLAN.read_text(encoding="utf-8")
        lowered = text.lower()
        command_blocks = "\n".join(
            re.findall(r"```(?:bash|text|yaml)?\n(.*?)```", text, flags=re.DOTALL)
        ).lower()

        self.assertIn("blocked until jamie explicitly approves scale-up", lowered)
        self.assertIn("do not run the 500-valid-pair gate", lowered)
        for phrase in [
            "provisional ranger-efficacy belief only",
            "not final criticality",
            "not soc control",
            "not publication-grade science",
            "not policy quality",
        ]:
            self.assertIn(phrase, lowered)
        self.assertNotRegex(command_blocks, r"(^|[;&|]\s*)puffer(\s|$)")
        self.assertNotRegex(command_blocks, r"\btrain\b|\beval\b|raylib|c_render")


if __name__ == "__main__":
    unittest.main()
