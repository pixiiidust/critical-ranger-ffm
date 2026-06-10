import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


class LocalWslPairedSignalCliTests(unittest.TestCase):
    def run_cli(self, args, *, cwd=None):
        command = [sys.executable, "-m", "critical_ranger_ffm.reporting.local_wsl_paired_signal_check", *args]
        return subprocess.run(
            command,
            cwd=cwd or REPO,
            text=True,
            capture_output=True,
            env={"PYTHONPATH": str(REPO / "src")},
            check=False,
        )

    def test_cli_refuses_fixture_sample_provider_for_issue_38_evidence(self):
        result = self.run_cli(
            [
                "--sample-provider",
                "critical_ranger_ffm.reporting.paired_signal_report:build_fixture_signal_rows",
                "--output-dir",
                str(REPO / ".tmp-does-not-matter"),
            ]
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("fixture sample providers are not valid #38 evidence", result.stderr)

    def test_cli_loads_real_local_provider_writes_artifacts_and_prints_review_summary(self):
        work = Path(tempfile.mkdtemp(prefix="cr-ffm-local-wsl-cli-"))
        provider = work / "real_provider.py"
        provider.write_text(
            textwrap.dedent(
                """
                from critical_ranger_ffm.reporting.paired_switch_point_runner import (
                    DeterministicSwitchPointState,
                    SwitchPointSample,
                )

                def collect_samples(target_valid_pairs, attempted_pair_cap, readout_horizon_steps, seed_start):
                    state = DeterministicSwitchPointState(
                        width=5,
                        height=5,
                        grid=[1] * 25,
                        seed=seed_start,
                        timestep=3,
                        step_cap=64,
                        lightning_schedule=[[], [], []],
                        regrowth_schedule=[[], [], []],
                    )
                    return [
                        SwitchPointSample(
                            pair_id="real-local-provider-contract",
                            episode_id="episode-real-contract",
                            pre_intervention_state=state,
                            ranger_index=12,
                            pair_seed=seed_start,
                        )
                    ]
                """
            ),
            encoding="utf-8",
        )
        output = work / "artifacts"

        result = self.run_cli(
            [
                "--sample-provider",
                "real_provider:collect_samples",
                "--provider-root",
                str(work),
                "--output-dir",
                str(output),
                "--target-valid-pairs",
                "1",
                "--attempted-pair-cap",
                "2",
                "--readout-horizon-steps",
                "3",
                "--seed-start",
                "3701",
            ]
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("verdict=", result.stdout)
        self.assertIn("valid_pairs=1", result.stdout)
        self.assertIn("attempted_pairs=1", result.stdout)
        self.assertIn("invalid_rate=0.000", result.stdout)
        self.assertIn("replay_status=ok", result.stdout)
        self.assertIn("runner_invariant_status=ok", result.stdout)
        self.assertIn("csv=", result.stdout)
        self.assertIn("markdown=", result.stdout)
        self.assertIn("json=", result.stdout)
        payload = json.loads((output / "paired_signal_summary.json").read_text(encoding="utf-8"))
        self.assertIn(payload["verdict"], {"pass_signal", "mixed_signal", "diagnostic_only", "invalid_runner"})
        self.assertEqual(payload["readout_horizon_steps"], 3)


if __name__ == "__main__":
    unittest.main()
