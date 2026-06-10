import json
import tempfile
import unittest
from pathlib import Path

from critical_ranger_ffm.reporting.paired_signal_report import (
    PairedSignalConfig,
    evaluate_paired_signal_report,
    load_paired_signal_rows,
)
from critical_ranger_ffm.reporting.paired_switch_point_runner import (
    DeterministicSwitchPointState,
    PairedSwitchPointConfig,
    SwitchPointSample,
    run_paired_switch_point_rows,
    write_paired_switch_point_artifacts,
)


class PairedSwitchPointRunnerTests(unittest.TestCase):
    def small_state(self, *, grid=None, lightning_schedule=None, regrowth_schedule=None, step_cap=32):
        return DeterministicSwitchPointState(
            width=5,
            height=5,
            grid=grid
            or [
                1, 1, 1, 1, 1,
                1, 1, 1, 1, 1,
                1, 1, 1, 1, 1,
                1, 1, 1, 1, 1,
                1, 1, 1, 1, 1,
            ],
            seed=3701,
            timestep=9,
            step_cap=step_cap,
            regrowth_schedule=regrowth_schedule or [[], [], []],
            lightning_schedule=lightning_schedule or [[7], [], []],
        )

    def test_runner_restores_same_pre_intervention_state_and_only_initial_branch_difference_is_cell(self):
        sample = SwitchPointSample(
            pair_id="pair-restore",
            episode_id="episode-a",
            pre_intervention_state=self.small_state(lightning_schedule=[[], []]),
            ranger_index=12,
            pair_seed=41,
        )

        row = run_paired_switch_point_rows([sample], PairedSwitchPointConfig(readout_horizon_steps=2))[0]

        self.assertEqual(row["valid_pair"], "true")
        self.assertEqual(row["validity_reason"], "ok")
        self.assertEqual(row["treatment_index"], "12")
        self.assertNotEqual(row["control_index"], "12")
        self.assertEqual(row["pre_restore_status"], "ok")
        self.assertEqual(row["initial_branch_difference_count"], "2")
        self.assertEqual(row["initial_branch_difference_indices"], f"12,{row['control_index']}")
        self.assertEqual(row["runner_invariant_status"], "ok")

    def test_runner_uses_7x7_same_tercile_density_control_and_quarantines_invalid_pairs(self):
        invalid_grid = [0] * 25
        invalid_grid[12] = 1
        for index in [0, 1, 2, 3, 5, 10, 15]:
            invalid_grid[index] = 1
        valid = SwitchPointSample(
            pair_id="pair-valid",
            episode_id="episode-b",
            pre_intervention_state=self.small_state(),
            ranger_index=12,
            pair_seed=42,
        )
        invalid = SwitchPointSample(
            pair_id="pair-invalid",
            episode_id="episode-b",
            pre_intervention_state=self.small_state(grid=invalid_grid),
            ranger_index=12,
            pair_seed=42,
        )

        rows = run_paired_switch_point_rows([valid, invalid])

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["match_quality"], "exact_tercile")
        self.assertEqual(rows[0]["ranger_density_tercile"], rows[0]["control_density_tercile"])
        self.assertEqual(rows[1]["valid_pair"], "false")
        self.assertEqual(rows[1]["validity_reason"], "no_same_tercile_control")
        self.assertEqual(rows[1]["match_quality"], "no_same_tercile_control")
        self.assertEqual(rows[1]["control_index"], "-1")

    def test_runner_freezes_readout_and_does_not_call_adaptive_policy_after_switch_point(self):
        def forbidden_policy(*_args, **_kwargs):
            raise AssertionError("adaptive policy must not be called during frozen read-out")

        sample = SwitchPointSample(
            pair_id="pair-frozen",
            episode_id="episode-c",
            pre_intervention_state=self.small_state(lightning_schedule=[[], [], []]),
            ranger_index=12,
            pair_seed=43,
            adaptive_policy=forbidden_policy,
        )

        row = run_paired_switch_point_rows([sample], PairedSwitchPointConfig(readout_horizon_steps=3))[0]

        self.assertEqual(row["valid_pair"], "true")
        self.assertEqual(row["frozen_readout_status"], "frozen")
        self.assertEqual(row["adaptive_policy_calls"], "0")

    def test_runner_records_configurable_readout_horizon_with_default_512(self):
        sample = SwitchPointSample(
            pair_id="pair-horizon",
            episode_id="episode-d",
            pre_intervention_state=self.small_state(lightning_schedule=[[], [], []]),
            ranger_index=12,
            pair_seed=44,
        )

        default_row = run_paired_switch_point_rows([sample])[0]
        custom_row = run_paired_switch_point_rows([sample], PairedSwitchPointConfig(readout_horizon_steps=3))[0]

        self.assertEqual(default_row["readout_horizon_steps"], "512")
        self.assertEqual(custom_row["readout_horizon_steps"], "3")

    def test_runner_uses_shared_post_intervention_replay_schedule_for_treatment_and_control(self):
        sample = SwitchPointSample(
            pair_id="pair-replay",
            episode_id="episode-e",
            pre_intervention_state=self.small_state(lightning_schedule=[[7], [8], []]),
            ranger_index=12,
            pair_seed=45,
        )

        row = run_paired_switch_point_rows([sample], PairedSwitchPointConfig(readout_horizon_steps=3))[0]

        self.assertEqual(row["replay_status"], "ok")
        self.assertEqual(row["shared_replay_steps"], "3")
        self.assertEqual(row["treatment_replay_fingerprint"], row["control_replay_fingerprint"])

    def test_invariant_and_replay_failures_are_hard_stop_invalid_runner_rows(self):
        invariant_bad = SwitchPointSample(
            pair_id="pair-invariant-bad",
            episode_id="episode-f",
            pre_intervention_state=self.small_state(lightning_schedule=[[], []]),
            ranger_index=12,
            pair_seed=46,
            inject_control_grid_mismatch_index=0,
        )
        replay_bad = SwitchPointSample(
            pair_id="pair-replay-bad",
            episode_id="episode-f",
            pre_intervention_state=self.small_state(lightning_schedule=[[], []]),
            ranger_index=12,
            pair_seed=47,
            control_lightning_schedule_override=[[0], []],
        )

        rows = run_paired_switch_point_rows(
            [invariant_bad, replay_bad],
            PairedSwitchPointConfig(readout_horizon_steps=2),
        )
        report = evaluate_paired_signal_report(rows, PairedSignalConfig(target_valid_pairs=1))

        self.assertEqual(rows[0]["valid_pair"], "false")
        self.assertEqual(rows[0]["runner_invariant_status"], "grid_mismatch")
        self.assertEqual(rows[0]["validity_reason"], "branch_invariant_failure")
        self.assertEqual(rows[1]["replay_status"], "mismatch")
        self.assertEqual(rows[1]["validity_reason"], "replay_mismatch")
        self.assertEqual(report.verdict, "invalid_runner")

    def test_one_runner_invocation_writes_paired_csv_markdown_and_json_report_contract(self):
        output = Path(tempfile.mkdtemp())
        samples = [
            SwitchPointSample(
                pair_id="pair-artifact",
                episode_id="episode-g",
                pre_intervention_state=self.small_state(lightning_schedule=[[7], [], []]),
                ranger_index=12,
                pair_seed=48,
            )
        ]

        artifacts = write_paired_switch_point_artifacts(
            samples,
            output,
            PairedSwitchPointConfig(readout_horizon_steps=3, run_id="issue37-smoke"),
        )

        self.assertEqual(set(artifacts), {"csv", "markdown", "json"})
        rows = load_paired_signal_rows(artifacts["csv"])
        self.assertEqual(rows[0]["run_id"], "issue37-smoke")
        self.assertEqual(rows[0]["evidence_label"], "signal_smoke_only")
        markdown = artifacts["markdown"].read_text(encoding="utf-8")
        self.assertIn("signal/smoke check only", markdown)
        payload = json.loads(artifacts["json"].read_text(encoding="utf-8"))
        self.assertEqual(payload["readout_horizon_steps"], 3)
        self.assertIn(payload["verdict"], {"pass_signal", "mixed_signal", "diagnostic_only", "invalid_runner"})


if __name__ == "__main__":
    unittest.main()
