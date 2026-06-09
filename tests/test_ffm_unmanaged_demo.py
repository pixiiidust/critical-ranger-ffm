import re
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
DEMO_SOURCE = REPO / "demos" / "ffm_unmanaged_demo.c"
ENV_SOURCE = REPO / "src" / "critical_ranger_ffm" / "ffm_unmanaged.c"
INCLUDE = REPO / "src" / "critical_ranger_ffm"
CONFIG = REPO / "configs" / "ffm_unmanaged_demo.ini"


class FfmUnmanagedDemoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.binary = self.tmp / "ffm_unmanaged_demo"

    def compile_demo(self):
        completed = subprocess.run(
            [
                "cc",
                "-std=c11",
                "-O2",
                "-Wall",
                "-Wextra",
                "-pedantic",
                "-I",
                str(INCLUDE),
                str(DEMO_SOURCE),
                str(ENV_SOURCE),
                "-o",
                str(self.binary),
            ],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)

    def run_demo(self, *args, expect_ok=True):
        self.compile_demo()
        completed = subprocess.run(
            [str(self.binary), *args],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        if expect_ok:
            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        else:
            self.assertNotEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        return completed

    def test_default_config_is_cpu_safe_small_debug_smoke(self):
        text = CONFIG.read_text(encoding="utf-8")
        self.assertIn("grid_width=8", text)
        self.assertIn("grid_height=8", text)
        self.assertIn("seed=20260610", text)
        self.assertIn("p=0.05", text)
        self.assertIn("f=0.02", text)
        self.assertIn("episode_step_cap=12", text)
        self.assertIn("smoke_step_cap=6", text)
        self.assertIn("debug_every=2", text)
        self.assertNotIn("puffer", text.lower())
        self.assertNotIn("gpu", text.lower())

    def test_config_drives_demo_output_shape_and_state_counters(self):
        completed = self.run_demo(
            "--config", str(CONFIG),
            "--grid-width", "4",
            "--grid-height", "3",
            "--seed", "99",
            "--p", "0.25",
            "--f", "0.125",
            "--episode-step-cap", "7",
            "--smoke-step-cap", "3",
            "--debug-every", "1",
        )
        stdout = completed.stdout
        self.assertIn("Critical Ranger FFM unmanaged demo smoke", stdout)
        self.assertIn("seed=99 grid=4x3 p=0.25 f=0.125 episode_step_cap=7 smoke_step_cap=3", stdout)
        self.assertRegex(stdout, r"step=0 empty=\d+ tree=\d+ burning=\d+")
        self.assertRegex(stdout, r"step=1 empty=\d+ tree=\d+ burning=\d+ active_before=\d+ active_after=\d+ regrowths=\d+ lightning=\d+ truncated=0")
        self.assertRegex(stdout, r"step=3 empty=\d+ tree=\d+ burning=\d+ active_before=\d+ active_after=\d+ regrowths=\d+ lightning=\d+ truncated=0")
        self.assertRegex(stdout, r"result=pass steps_run=3 truncated=0 empty=\d+ tree=\d+ burning=\d+ total_cells=12")

    def test_same_seed_and_config_produce_identical_demo_output(self):
        args = (
            "--config", str(CONFIG),
            "--grid-width", "5",
            "--grid-height", "5",
            "--seed", "4242",
            "--p", "0.1",
            "--f", "0.05",
            "--episode-step-cap", "10",
            "--smoke-step-cap", "4",
            "--debug-every", "2",
        )
        first = self.run_demo(*args).stdout
        second = self.run_demo(*args).stdout
        self.assertEqual(first, second)
        step_lines = [line for line in first.splitlines() if re.match(r"step=", line)]
        self.assertGreaterEqual(len(step_lines), 3)

    def test_invalid_config_exits_nonzero_with_clear_error(self):
        bad_config = self.tmp / "bad.ini"
        bad_config.write_text("grid_width=0\ngrid_height=4\np=1.5\n", encoding="utf-8")
        completed = self.run_demo("--config", str(bad_config), expect_ok=False)
        self.assertIn("ERROR:", completed.stderr)
        self.assertIn("invalid unmanaged demo config", completed.stderr)


if __name__ == "__main__":
    unittest.main()
