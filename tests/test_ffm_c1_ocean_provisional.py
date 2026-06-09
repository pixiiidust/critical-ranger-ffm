import subprocess
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "src" / "critical_ranger_ffm" / "ocean" / "ffm_c1_ocean_provisional.c"
CONFIG = REPO / "configs" / "ffm_c1_ocean_provisional.ini"


class FfmC1OceanProvisionalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.binary = self.tmp / "ffm_c1_ocean_provisional"

    def compile_demo(self):
        completed = subprocess.run(
            [
                "cc",
                "-std=c11",
                "-O2",
                "-Wall",
                "-Wextra",
                "-pedantic",
                "-DFFM_C1_PROVISIONAL_DEMO",
                str(SOURCE),
                "-o",
                str(self.binary),
            ],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)

    def run_demo(self, *args):
        self.compile_demo()
        completed = subprocess.run(
            [str(self.binary), *args],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        return completed

    def test_config_is_provisional_small_debug_grid(self):
        text = CONFIG.read_text(encoding="utf-8")
        self.assertIn("PROVISIONAL/SUPERCRITICAL", text)
        self.assertIn("grid_width=32", text)
        self.assertIn("grid_height=32", text)
        self.assertNotIn("grid_width=128", text)
        self.assertNotIn("grid_height=128", text)
        self.assertIn("dummy_reward=0.0", text)

    def test_self_test_covers_action_observation_and_step_boundaries(self):
        completed = self.run_demo("--self-test")
        self.assertIn("c1 provisional self-test: PASS", completed.stdout)

    def test_random_demo_uses_full_flat_action_space_including_noop(self):
        completed = self.run_demo("--config", str(CONFIG), "--demo-steps", "4096")
        self.assertIn("C1 provisional random-action demo", completed.stdout)
        self.assertIn("grid=32x32", completed.stdout)
        self.assertIn("actions=1025", completed.stdout)
        self.assertIn("obs=3072", completed.stdout)
        self.assertIn("saw_cell=1", completed.stdout)
        self.assertIn("saw_noop=1", completed.stdout)


if __name__ == "__main__":
    unittest.main()
