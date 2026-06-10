import unittest

from critical_ranger_ffm.reporting.paired_switch_point_runner import SwitchPointSample


class LocalWslRealSampleProviderTests(unittest.TestCase):
    def test_provider_builds_switch_point_samples_from_real_c_environment(self):
        from critical_ranger_ffm.reporting.local_wsl_sample_provider import (
            build_local_wsl_switch_point_samples,
        )

        samples = list(
            build_local_wsl_switch_point_samples(
                target_valid_pairs=2,
                attempted_pair_cap=5,
                readout_horizon_steps=3,
                seed_start=3801,
            )
        )

        self.assertEqual(len(samples), 2)
        for sample in samples:
            self.assertIsInstance(sample, SwitchPointSample)
            state = sample.pre_intervention_state
            self.assertEqual(state.width, 32)
            self.assertEqual(state.height, 32)
            self.assertEqual(len(state.grid), 32 * 32)
            self.assertGreater(state.timestep, 0)
            self.assertGreater(state.step_cap, state.timestep + 3)
            self.assertIn(state.grid[sample.ranger_index], {1, 2})
            self.assertNotIn("fixture", sample.pair_id.lower())

    def test_provider_uses_attempt_cap_instead_of_synthesizing_fixture_rows(self):
        from critical_ranger_ffm.reporting.local_wsl_sample_provider import (
            build_local_wsl_switch_point_samples,
        )

        samples = list(
            build_local_wsl_switch_point_samples(
                target_valid_pairs=3,
                attempted_pair_cap=1,
                readout_horizon_steps=2,
                seed_start=3901,
            )
        )

        self.assertLessEqual(len(samples), 1)
        self.assertTrue(all(isinstance(sample, SwitchPointSample) for sample in samples))


if __name__ == "__main__":
    unittest.main()
