from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, cast

from critical_ranger_ffm.reporting.paired_signal_report import (
    EVIDENCE_LABEL_SIGNAL_SMOKE_ONLY,
    PAIRED_SIGNAL_CSV_COLUMNS,
    PairedSignalConfig,
    evaluate_paired_signal_report,
    write_paired_signal_artifacts,
)

EMPTY = 0
TREE = 1
BURNING = 2


@dataclass(frozen=True)
class PairedSwitchPointConfig:
    readout_horizon_steps: int = 512
    invalid_rate_diagnostic_threshold: float = 0.25
    target_valid_pairs: int = 100
    attempted_pair_cap: int = 150
    run_id: str = "paired-switch-point-runner"
    config_id: str = "deterministic-cpu-switch-point-v1"
    protocol_id: str = "switch-point-test-protocol-v1"
    schema_version: str = "1"

    def __post_init__(self) -> None:
        if self.readout_horizon_steps <= 0:
            raise ValueError("readout_horizon_steps must be positive")


@dataclass(frozen=True)
class DeterministicSwitchPointState:
    width: int
    height: int
    grid: list[int]
    seed: int
    timestep: int
    step_cap: int
    regrowth_schedule: list[list[int]] = field(default_factory=list)
    lightning_schedule: list[list[int]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("width and height must be positive")
        if len(self.grid) != self.width * self.height:
            raise ValueError("grid length must equal width * height")
        if self.step_cap <= 0:
            raise ValueError("step_cap must be positive")
        invalid = [cell for cell in self.grid if cell not in {EMPTY, TREE, BURNING}]
        if invalid:
            raise ValueError("grid cells must be 0 empty, 1 tree, or 2 burning")


@dataclass(frozen=True)
class SwitchPointSample:
    pair_id: str
    episode_id: str
    pre_intervention_state: DeterministicSwitchPointState
    ranger_index: int
    pair_seed: int
    adaptive_policy: Callable[..., object] | None = None
    inject_control_grid_mismatch_index: int | None = None
    control_lightning_schedule_override: list[list[int]] | None = None
    control_regrowth_schedule_override: list[list[int]] | None = None


def run_paired_switch_point_rows(
    samples: Iterable[SwitchPointSample],
    config: PairedSwitchPointConfig | None = None,
) -> list[dict[str, str]]:
    config = config or PairedSwitchPointConfig()
    return [_run_one_sample(index, sample, config) for index, sample in enumerate(samples)]


def write_paired_switch_point_artifacts(
    samples: Iterable[SwitchPointSample],
    out_dir: Path,
    config: PairedSwitchPointConfig | None = None,
) -> dict[str, Path]:
    config = config or PairedSwitchPointConfig()
    rows = run_paired_switch_point_rows(samples, config)
    contract_rows = [_contract_row(row) for row in rows]
    report = evaluate_paired_signal_report(
        contract_rows,
        PairedSignalConfig(
            invalid_rate_diagnostic_threshold=config.invalid_rate_diagnostic_threshold,
            target_valid_pairs=config.target_valid_pairs,
            attempted_pair_cap=config.attempted_pair_cap,
            default_readout_horizon_steps=config.readout_horizon_steps,
            schema_version=config.schema_version,
        ),
    )
    return write_paired_signal_artifacts(report, out_dir)


def _run_one_sample(index: int, sample: SwitchPointSample, config: PairedSwitchPointConfig) -> dict[str, str]:
    state = sample.pre_intervention_state
    base = _base_row(index, sample, config)
    if sample.ranger_index < 0 or sample.ranger_index >= len(state.grid):
        return _invalid_row(base, "invalid_ranger_index", "invalid", "invalid")

    control = _select_density_matched_control(state, sample.ranger_index, sample.pair_seed)
    _add_match_fields(base, state, sample.ranger_index, control)
    if not control["valid"]:
        return _invalid_row(base, cast(str, control["reason"]), "ok", "ok")

    control_index = int(cast(int, control["control_index"]))
    treatment_grid = list(state.grid)
    control_grid = list(state.grid)
    treatment_grid[sample.ranger_index] = EMPTY
    control_grid[control_index] = EMPTY

    pre_restore_ok = treatment_grid != state.grid and control_grid != state.grid and list(state.grid) == list(sample.pre_intervention_state.grid)
    base["pre_restore_status"] = "ok" if pre_restore_ok else "mismatch"
    diff_indices = [i for i, (left, right) in enumerate(zip(treatment_grid, control_grid)) if left != right]
    base["initial_branch_difference_count"] = str(len(diff_indices))
    base["initial_branch_difference_indices"] = ",".join(str(i) for i in diff_indices)
    base["frozen_readout_status"] = "frozen"
    base["adaptive_policy_calls"] = "0"

    invariant_status = "ok"
    if sorted(diff_indices) != sorted([sample.ranger_index, control_index]):
        invariant_status = "grid_mismatch"
    if sample.inject_control_grid_mismatch_index is not None:
        mismatch_index = sample.inject_control_grid_mismatch_index
        if 0 <= mismatch_index < len(control_grid):
            control_grid[mismatch_index] = EMPTY if control_grid[mismatch_index] != EMPTY else TREE
        invariant_status = "grid_mismatch"
    if invariant_status != "ok":
        base["runner_invariant_status"] = invariant_status
        return _invalid_row(base, "branch_invariant_failure", invariant_status, "ok")

    treatment_regrowth = _schedule_for_horizon(state.regrowth_schedule, config.readout_horizon_steps)
    treatment_lightning = _schedule_for_horizon(state.lightning_schedule, config.readout_horizon_steps)
    control_regrowth = _schedule_for_horizon(
        sample.control_regrowth_schedule_override
        if sample.control_regrowth_schedule_override is not None
        else state.regrowth_schedule,
        config.readout_horizon_steps,
    )
    control_lightning = _schedule_for_horizon(
        sample.control_lightning_schedule_override
        if sample.control_lightning_schedule_override is not None
        else state.lightning_schedule,
        config.readout_horizon_steps,
    )
    treatment_fp = _fingerprint_schedule(treatment_regrowth, treatment_lightning)
    control_fp = _fingerprint_schedule(control_regrowth, control_lightning)
    base["shared_replay_steps"] = str(config.readout_horizon_steps)
    base["treatment_replay_fingerprint"] = treatment_fp
    base["control_replay_fingerprint"] = control_fp
    if treatment_fp != control_fp:
        return _invalid_row(base, "replay_mismatch", "ok", "mismatch")

    treatment_burned, treatment_trees, treatment_truncated = _run_readout(
        state.width,
        state.height,
        treatment_grid,
        treatment_regrowth,
        treatment_lightning,
        state.timestep,
        state.step_cap,
    )
    control_burned, control_trees, control_truncated = _run_readout(
        state.width,
        state.height,
        control_grid,
        control_regrowth,
        control_lightning,
        state.timestep,
        state.step_cap,
    )
    if treatment_truncated or control_truncated:
        base["truncation_status"] = "truncated"
        return _invalid_row(base, "readout_truncated", "truncated", "ok")

    cell_count = state.width * state.height
    base.update(
        {
            "valid_pair": "true",
            "validity_reason": "ok",
            "treatment_burned_cells": str(treatment_burned),
            "control_burned_cells": str(control_burned),
            "burned_area_avoided_delta": str(control_burned - treatment_burned),
            "treatment_living_tree_fraction": f"{treatment_trees / cell_count:.3f}",
            "control_living_tree_fraction": f"{control_trees / cell_count:.3f}",
            "living_tree_fraction_delta": f"{(treatment_trees - control_trees) / cell_count:.3f}",
            "runner_invariant_status": "ok",
            "replay_status": "ok",
            "truncation_status": "ok",
        }
    )
    return base


def _base_row(index: int, sample: SwitchPointSample, config: PairedSwitchPointConfig) -> dict[str, str]:
    state = sample.pre_intervention_state
    row, col = divmod(sample.ranger_index, state.width) if 0 <= sample.ranger_index < len(state.grid) else (-1, -1)
    return {
        "schema_version": config.schema_version,
        "run_id": config.run_id,
        "pair_id": sample.pair_id or f"pair-{index:03d}",
        "seed": str(sample.pair_seed),
        "episode_id": sample.episode_id,
        "timestep": str(state.timestep),
        "treatment_row": str(row),
        "treatment_col": str(col),
        "treatment_index": str(sample.ranger_index),
        "control_row": "-1",
        "control_col": "-1",
        "control_index": "-1",
        "ranger_density_trees_7x7": "",
        "ranger_density_cells_7x7": "",
        "ranger_density_tercile": "invalid",
        "control_density_trees_7x7": "",
        "control_density_cells_7x7": "",
        "control_density_tercile": "invalid",
        "match_quality": "invalid",
        "valid_pair": "false",
        "validity_reason": "not_run",
        "treatment_burned_cells": "0",
        "control_burned_cells": "0",
        "burned_area_avoided_delta": "0",
        "treatment_living_tree_fraction": "0.000",
        "control_living_tree_fraction": "0.000",
        "living_tree_fraction_delta": "0.000",
        "readout_horizon_steps": str(config.readout_horizon_steps),
        "config_id": config.config_id,
        "protocol_id": config.protocol_id,
        "runner_invariant_status": "ok",
        "replay_status": "ok",
        "evidence_label": EVIDENCE_LABEL_SIGNAL_SMOKE_ONLY,
        "pre_restore_status": "not_run",
        "initial_branch_difference_count": "0",
        "initial_branch_difference_indices": "",
        "frozen_readout_status": "frozen",
        "adaptive_policy_calls": "0",
        "shared_replay_steps": "0",
        "treatment_replay_fingerprint": "",
        "control_replay_fingerprint": "",
        "truncation_status": "not_run",
    }


def _invalid_row(base: dict[str, str], reason: str, invariant_status: str, replay_status: str) -> dict[str, str]:
    base.update(
        {
            "valid_pair": "false",
            "validity_reason": reason,
            "runner_invariant_status": invariant_status,
            "replay_status": replay_status,
            "evidence_label": EVIDENCE_LABEL_SIGNAL_SMOKE_ONLY,
        }
    )
    return base


def _add_match_fields(base: dict[str, str], state: DeterministicSwitchPointState, ranger_index: int, match: dict[str, object]) -> None:
    base.update(
        {
            "ranger_density_trees_7x7": str(match["ranger_density_trees"]),
            "ranger_density_cells_7x7": str(match["ranger_density_cells"]),
            "ranger_density_tercile": str(match["ranger_tercile"]),
            "control_density_trees_7x7": str(match.get("control_density_trees", "")),
            "control_density_cells_7x7": str(match.get("control_density_cells", "")),
            "control_density_tercile": str(match.get("control_tercile", "invalid")),
            "match_quality": "exact_tercile" if match["valid"] else str(match["reason"]),
        }
    )
    if match["valid"]:
        control_index = int(cast(int, match["control_index"]))
        row, col = divmod(control_index, state.width)
        base.update({"control_index": str(control_index), "control_row": str(row), "control_col": str(col)})


def _select_density_matched_control(state: DeterministicSwitchPointState, ranger_index: int, pair_seed: int) -> dict[str, object]:
    ranger_trees, ranger_cells, ranger_tercile = _density_7x7(state, ranger_index)
    candidates: list[tuple[int, int, int, str]] = []
    total_candidates = 0
    for index, cell in enumerate(state.grid):
        if index == ranger_index or cell != TREE:
            continue
        total_candidates += 1
        trees, cells, tercile = _density_7x7(state, index)
        if tercile == ranger_tercile:
            candidates.append((index, trees, cells, tercile))
    if not candidates:
        return {
            "valid": False,
            "reason": "no_same_tercile_control",
            "ranger_density_trees": ranger_trees,
            "ranger_density_cells": ranger_cells,
            "ranger_tercile": ranger_tercile,
            "total_candidate_count": total_candidates,
            "same_tercile_candidate_count": 0,
        }
    selected = candidates[pair_seed % len(candidates)]
    return {
        "valid": True,
        "reason": "ok",
        "control_index": selected[0],
        "ranger_density_trees": ranger_trees,
        "ranger_density_cells": ranger_cells,
        "ranger_tercile": ranger_tercile,
        "control_density_trees": selected[1],
        "control_density_cells": selected[2],
        "control_tercile": selected[3],
        "total_candidate_count": total_candidates,
        "same_tercile_candidate_count": len(candidates),
    }


def _density_7x7(state: DeterministicSwitchPointState, center: int) -> tuple[int, int, str]:
    row, col = divmod(center, state.width)
    trees = 0
    cells = 0
    for rr in range(max(0, row - 3), min(state.height - 1, row + 3) + 1):
        for cc in range(max(0, col - 3), min(state.width - 1, col + 3) + 1):
            at = rr * state.width + cc
            if at == center:
                continue
            cells += 1
            if state.grid[at] == TREE:
                trees += 1
    if cells <= 0:
        return trees, cells, "invalid"
    if trees * 3 < cells:
        return trees, cells, "low"
    if trees * 3 < cells * 2:
        return trees, cells, "mid"
    return trees, cells, "high"


def _schedule_for_horizon(schedule: list[list[int]], horizon: int) -> list[list[int]]:
    return [list(schedule[step]) if step < len(schedule) else [] for step in range(horizon)]


def _fingerprint_schedule(regrowth: list[list[int]], lightning: list[list[int]]) -> str:
    material = repr((regrowth, lightning)).encode("utf-8")
    return hashlib.sha256(material).hexdigest()[:16]


def _run_readout(
    width: int,
    height: int,
    grid: list[int],
    regrowth_schedule: list[list[int]],
    lightning_schedule: list[list[int]],
    start_timestep: int,
    step_cap: int,
) -> tuple[int, int, bool]:
    working = list(grid)
    burned: set[int] = set()
    for step, (regrowth_indices, lightning_indices) in enumerate(zip(regrowth_schedule, lightning_schedule), start=1):
        for index in regrowth_indices:
            if 0 <= index < len(working) and working[index] == EMPTY:
                working[index] = TREE
        for index in lightning_indices:
            if 0 <= index < len(working) and working[index] == TREE:
                working[index] = BURNING
        next_grid = list(working)
        for index, cell in enumerate(working):
            if cell == BURNING:
                burned.add(index)
                next_grid[index] = EMPTY
            elif cell == TREE and _has_burning_neighbor(working, index, width, height):
                next_grid[index] = BURNING
        working = next_grid
        if start_timestep + step >= step_cap:
            return len(burned), working.count(TREE), True
    return len(burned), working.count(TREE), False


def _has_burning_neighbor(grid: list[int], index: int, width: int, height: int) -> bool:
    row, col = divmod(index, width)
    neighbors = []
    if row > 0:
        neighbors.append(index - width)
    if row + 1 < height:
        neighbors.append(index + width)
    if col > 0:
        neighbors.append(index - 1)
    if col + 1 < width:
        neighbors.append(index + 1)
    return any(grid[neighbor] == BURNING for neighbor in neighbors)


def _contract_row(row: dict[str, str]) -> dict[str, str]:
    return {column: row[column] for column in PAIRED_SIGNAL_CSV_COLUMNS}
