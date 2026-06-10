import subprocess
import sys
import unittest


class LocalWslBeliefGateCliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "critical_ranger_ffm.reporting.local_wsl_belief_gate_check", *args],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_help_documents_local_wsl_belief_gate_defaults_and_outputs(self):
        result = self.run_cli("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Local WSL 500-valid-pair belief gate", result.stdout)
        self.assertIn("--target-valid-pairs TARGET_VALID_PAIRS", result.stdout)
        self.assertIn("--attempted-pair-cap ATTEMPTED_PAIR_CAP", result.stdout)
        self.assertIn("--min-independent-seeds MIN_INDEPENDENT_SEEDS", result.stdout)
        self.assertIn("--max-valid-pairs-per-seed MAX_VALID_PAIRS_PER_SEED", result.stdout)
        self.assertIn("belief_gate_report.md", result.stdout)
        self.assertIn("belief_gate_summary.json", result.stdout)

    def test_cli_refuses_fixture_provider_before_runtime(self):
        result = self.run_cli(
            "--sample-provider",
            "critical_ranger_ffm.reporting.paired_signal_report:build_fixture_signal_rows",
            "--output-dir",
            "/tmp/critical-ranger-ffm-belief-cli-test",
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("fixture sample providers are not valid belief-gate evidence", result.stderr)
        self.assertNotIn("pass_belief_gate", result.stdout)


if __name__ == "__main__":
    unittest.main()
