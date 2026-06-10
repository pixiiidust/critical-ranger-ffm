from __future__ import annotations

import json
import subprocess
import tempfile
import textwrap
from pathlib import Path
from typing import Any

from critical_ranger_ffm.reporting.paired_switch_point_runner import (
    DeterministicSwitchPointState,
    SwitchPointSample,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_INCLUDE_DIR = _REPO_ROOT / "src" / "critical_ranger_ffm"
_UNMANAGED_SOURCE = _INCLUDE_DIR / "ffm_unmanaged.c"


def build_local_wsl_switch_point_samples(
    *,
    target_valid_pairs: int,
    attempted_pair_cap: int,
    readout_horizon_steps: int,
    seed_start: int,
) -> list[SwitchPointSample]:
    """Build #38 switch-point samples from the real unmanaged C environment.

    This is the smallest reviewed local WSL provider for the bridge CLI: it
    compiles a tiny helper against ``ffm_unmanaged.c``, advances real FFM envs,
    snapshots their grids, and returns ``SwitchPointSample`` objects for the
    paired report runner. It is not a fixture provider and it does not use GPU,
    Puffer train/eval, render, raylib, or policy-quality claims.
    """

    if target_valid_pairs <= 0:
        raise ValueError("target_valid_pairs must be positive")
    if attempted_pair_cap <= 0:
        raise ValueError("attempted_pair_cap must be positive")
    if readout_horizon_steps <= 0:
        raise ValueError("readout_horizon_steps must be positive")

    records = _run_c_sample_helper(
        target_valid_pairs=target_valid_pairs,
        attempted_pair_cap=attempted_pair_cap,
        readout_horizon_steps=readout_horizon_steps,
        seed_start=seed_start,
    )
    return [_record_to_sample(record, readout_horizon_steps) for record in records]


def _run_c_sample_helper(
    *,
    target_valid_pairs: int,
    attempted_pair_cap: int,
    readout_horizon_steps: int,
    seed_start: int,
) -> list[dict[str, Any]]:
    if not _UNMANAGED_SOURCE.exists():
        raise FileNotFoundError(f"missing unmanaged environment source: {_UNMANAGED_SOURCE}")

    with tempfile.TemporaryDirectory(prefix="critical-ranger-ffm-provider-") as tmpdir:
        tmp = Path(tmpdir)
        helper = tmp / "sample_provider_helper.c"
        binary = tmp / "sample_provider_helper"
        helper.write_text(_HELPER_SOURCE, encoding="utf-8")
        compile_result = subprocess.run(
            [
                "cc",
                "-std=c11",
                "-O2",
                "-Wall",
                "-Wextra",
                "-pedantic",
                "-I",
                str(_INCLUDE_DIR),
                str(helper),
                str(_UNMANAGED_SOURCE),
                "-o",
                str(binary),
            ],
            cwd=_REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if compile_result.returncode != 0:
            raise RuntimeError("failed to compile real C environment sample helper: " + compile_result.stderr.strip())

        run_result = subprocess.run(
            [
                str(binary),
                str(target_valid_pairs),
                str(attempted_pair_cap),
                str(readout_horizon_steps),
                str(seed_start),
            ],
            cwd=_REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if run_result.returncode != 0:
            raise RuntimeError("real C environment sample helper failed: " + run_result.stderr.strip())

    records: list[dict[str, Any]] = []
    for line in run_result.stdout.splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def _record_to_sample(record: dict[str, Any], readout_horizon_steps: int) -> SwitchPointSample:
    width = int(record["width"])
    height = int(record["height"])
    grid = [int(cell) for cell in record["grid"]]
    timestep = int(record["timestep"])
    state = DeterministicSwitchPointState(
        width=width,
        height=height,
        grid=grid,
        seed=int(record["seed"]),
        timestep=timestep,
        step_cap=max(int(record["step_cap"]), timestep + readout_horizon_steps + 1),
    )
    return SwitchPointSample(
        pair_id=str(record["pair_id"]),
        episode_id=str(record["episode_id"]),
        pre_intervention_state=state,
        ranger_index=int(record["ranger_index"]),
        pair_seed=int(record["pair_seed"]),
    )


_HELPER_SOURCE = textwrap.dedent(
    r'''
    #include "ffm_unmanaged.h"

    #include <stdint.h>
    #include <stdio.h>
    #include <stdlib.h>

    static int parse_int(const char *text, int fallback) {
        char *end = NULL;
        long value = strtol(text, &end, 10);
        if (!text || end == text || *end != '\0') return fallback;
        if (value < 0 || value > 2147483647L) return fallback;
        return (int)value;
    }

    static int find_ranger_index(const CrFfmEnv *env, uint64_t pair_seed) {
        for (int i = 0; i < env->cell_count; i++) {
            if (env->grid[i] != CR_FFM_TREE && env->grid[i] != CR_FFM_BURNING) continue;
            CrFfmControlMatch match = cr_ffm_select_density_matched_control(env, i, pair_seed);
            if (match.valid) return i;
        }
        return -1;
    }

    static void print_sample_json(int sample_index, const CrFfmEnv *env, int ranger_index, uint64_t pair_seed) {
        printf("{\"pair_id\":\"real-c-env-pair-%03d\",", sample_index);
        printf("\"episode_id\":\"real-c-env-seed-%llu\",", (unsigned long long)env->cfg.seed);
        printf("\"width\":%d,\"height\":%d,", env->cfg.grid_width, env->cfg.grid_height);
        printf("\"seed\":%llu,\"timestep\":%d,\"step_cap\":%d,", (unsigned long long)env->cfg.seed, env->step_count, env->cfg.episode_step_cap);
        printf("\"ranger_index\":%d,\"pair_seed\":%llu,\"grid\":[", ranger_index, (unsigned long long)pair_seed);
        for (int i = 0; i < env->cell_count; i++) {
            if (i) printf(",");
            printf("%u", (unsigned int)env->grid[i]);
        }
        printf("]}\n");
    }

    int main(int argc, char **argv) {
        if (argc != 5) {
            fprintf(stderr, "usage: helper target attempted_cap horizon seed_start\n");
            return 2;
        }
        int target = parse_int(argv[1], 0);
        int attempted_cap = parse_int(argv[2], 0);
        int horizon = parse_int(argv[3], 0);
        int seed_start = parse_int(argv[4], 0);
        if (target <= 0 || attempted_cap <= 0 || horizon <= 0) return 2;

        int produced = 0;
        for (int attempt = 0; attempt < attempted_cap && produced < target; attempt++) {
            CrFfmConfig cfg = cr_ffm_default_config();
            cfg.grid_width = 32;
            cfg.grid_height = 32;
            cfg.seed = (uint64_t)(seed_start + attempt);
            cfg.episode_step_cap = horizon + 64;
            cfg.initial_tree_density = 0.55;
            CrFfmEnv env;
            if (!cr_ffm_init(&env, &cfg)) return 3;
            for (int step = 0; step < 8; step++) {
                cr_ffm_step_unmanaged(&env);
            }
            uint64_t pair_seed = (uint64_t)(seed_start + attempt);
            int ranger_index = find_ranger_index(&env, pair_seed);
            if (ranger_index >= 0) {
                print_sample_json(produced, &env, ranger_index, pair_seed);
                produced++;
            }
            cr_ffm_free(&env);
        }
        return 0;
    }
    '''
)
