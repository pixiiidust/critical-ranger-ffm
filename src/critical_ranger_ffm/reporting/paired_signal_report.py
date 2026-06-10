from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, median
from typing import Any

VALID_SIGNAL_VERDICTS = {"pass_signal", "mixed_signal", "diagnostic_only", "invalid_runner"}
EVIDENCE_LABEL_SIGNAL_SMOKE_ONLY = "signal_smoke_only"
OK_STATUS = "ok"

PAIRED_SIGNAL_CSV_COLUMNS = [
    "schema_version",
    "run_id",
    "pair_id",
    "seed",
    "episode_id",
    "timestep",
    "treatment_row",
    "treatment_col",
    "treatment_index",
    "control_row",
    "control_col",
    "control_index",
    "ranger_density_trees_7x7",
    "ranger_density_cells_7x7",
    "ranger_density_tercile",
    "control_density_trees_7x7",
    "control_density_cells_7x7",
    "control_density_tercile",
    "match_quality",
    "valid_pair",
    "validity_reason",
    "treatment_burned_cells",
    "control_burned_cells",
    "burned_area_avoided_delta",
    "treatment_living_tree_fraction",
    "control_living_tree_fraction",
    "living_tree_fraction_delta",
    "readout_horizon_steps",
    "config_id",
    "protocol_id",
    "runner_invariant_status",
    "replay_status",
    "evidence_label",
]


@dataclass(frozen=True)
class PairedSignalConfig:
    invalid_rate_diagnostic_threshold: float = 0.25
    target_valid_pairs: int = 100
    attempted_pair_cap: int = 150
    default_readout_horizon_steps: int = 512
    schema_version: str = "1"


@dataclass(frozen=True)
class PairedSignalReport:
    rows: list[dict[str, str]]
    verdict: str
    evidence_label: str
    valid_pairs: int
    attempted_pairs: int
    invalid_pairs: int
    invalid_rate: float
    mean_burned_area_avoided: float | None
    median_burned_area_avoided: float | None
    percent_ranger_avoided_more_burned_area: float | None
    uncertainty_interval: dict[str, float | None]
    density_match_diagnostics: dict[str, Any]
    replay_status: str
    runner_invariant_status: str
    seed_schedule: dict[str, Any]
    readout_horizon_steps: int
    config_id: str
    protocol_id: str
    run_id: str
    schema_version: str = "1"
    notes: list[str] = field(default_factory=list)

    @classmethod
    def from_fixture_rows(
        cls,
        rows: list[dict[str, str]],
        config: PairedSignalConfig | None = None,
    ) -> "PairedSignalReport":
        return evaluate_paired_signal_report(rows, config)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "verdict": self.verdict,
            "evidence_label": self.evidence_label,
            "valid_pairs": self.valid_pairs,
            "attempted_pairs": self.attempted_pairs,
            "invalid_pairs": self.invalid_pairs,
            "invalid_rate": self.invalid_rate,
            "mean_burned_area_avoided": self.mean_burned_area_avoided,
            "median_burned_area_avoided": self.median_burned_area_avoided,
            "percent_ranger_avoided_more_burned_area": self.percent_ranger_avoided_more_burned_area,
            "uncertainty_interval": self.uncertainty_interval,
            "density_match_diagnostics": self.density_match_diagnostics,
            "replay_status": self.replay_status,
            "runner_invariant_status": self.runner_invariant_status,
            "seed_schedule": self.seed_schedule,
            "readout_horizon_steps": self.readout_horizon_steps,
            "config_id": self.config_id,
            "protocol_id": self.protocol_id,
        }

    def to_markdown(self) -> str:
        mean_value = _format_optional_float(self.mean_burned_area_avoided)
        median_value = _format_optional_float(self.median_burned_area_avoided)
        pct_value = _format_optional_percent(self.percent_ranger_avoided_more_burned_area)
        lo = _format_optional_float(self.uncertainty_interval.get("low"))
        hi = _format_optional_float(self.uncertainty_interval.get("high"))
        seed_values = ", ".join(str(seed) for seed in self.seed_schedule.get("seeds", [])) or "none"
        density_lines = [
            f"- Exact tercile matches: {self.density_match_diagnostics.get('exact_tercile_match_count', 0)}",
            f"- Valid match-quality mean: {_format_optional_float(self.density_match_diagnostics.get('mean_match_quality'))}",
            f"- Invalid reasons: {self.density_match_diagnostics.get('invalid_reasons', {})}",
        ]
        notes = "\n".join(f"- {note}" for note in self.notes) if self.notes else "- none"
        return "\n".join(
            [
                "# Paired switch-point signal report",
                "",
                f"Verdict: `{self.verdict}`",
                f"Evidence label: `{self.evidence_label}`",
                "",
                "This is a signal/smoke check only. It is not belief evidence and does not prove ranger efficacy.",
                "",
                "## Required metrics",
                "",
                f"- Valid pairs: {self.valid_pairs}",
                f"- Attempted pairs: {self.attempted_pairs}",
                f"- Invalid rate: {self.invalid_rate:.1%}",
                f"- Mean burned-area avoided: {mean_value}",
                f"- Median burned-area avoided: {median_value}",
                f"- Ranger avoided more burned area: {pct_value}",
                f"- Uncertainty interval: [{lo}, {hi}]",
                f"- Replay status: `{self.replay_status}`",
                f"- Runner invariant status: `{self.runner_invariant_status}`",
                f"- Seed schedule: {seed_values}",
                f"- Read-out horizon: {self.readout_horizon_steps} steps",
                "",
                "## Density-match diagnostics:",
                "",
                *density_lines,
                "",
                "## Notes",
                "",
                notes,
            ]
        )


def load_paired_signal_rows(path: Path) -> list[dict[str, str]]:
    path = Path(path)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        missing = [column for column in PAIRED_SIGNAL_CSV_COLUMNS if column not in fieldnames]
        if missing:
            raise ValueError(f"missing required paired signal columns: {', '.join(missing)}")
        rows = list(reader)
    for index, row in enumerate(rows, start=2):
        _parse_bool(row["valid_pair"], f"valid_pair on line {index}")
        _non_negative_int(row["seed"], f"seed on line {index}")
        _non_negative_int(row["timestep"], f"timestep on line {index}")
        _positive_int(row["readout_horizon_steps"], f"readout_horizon_steps on line {index}")
        if row["evidence_label"] != EVIDENCE_LABEL_SIGNAL_SMOKE_ONLY:
            raise ValueError(f"evidence_label on line {index} must be {EVIDENCE_LABEL_SIGNAL_SMOKE_ONLY}")
        if row["valid_pair"].lower() == "true" and row["validity_reason"] != "ok":
            raise ValueError(f"valid pair on line {index} must use validity_reason=ok")
    return rows


def evaluate_paired_signal_report(
    rows: list[dict[str, str]],
    config: PairedSignalConfig | None = None,
) -> PairedSignalReport:
    config = config or PairedSignalConfig()
    attempted = len(rows)
    valid_rows = [row for row in rows if _parse_bool(row["valid_pair"], "valid_pair")]
    invalid_rows = [row for row in rows if not _parse_bool(row["valid_pair"], "valid_pair")]
    invalid_rate = (len(invalid_rows) / attempted) if attempted else 0.0
    deltas = [_parse_float(row["burned_area_avoided_delta"], "burned_area_avoided_delta") for row in valid_rows]
    positive_count = sum(1 for delta in deltas if delta > 0)
    mean_delta = mean(deltas) if deltas else None
    median_delta = median(deltas) if deltas else None
    percent_positive = (100.0 * positive_count / len(deltas)) if deltas else None
    interval = _simple_uncertainty_interval(deltas)
    replay_status = _combined_status(rows, "replay_status")
    invariant_status = _combined_status(rows, "runner_invariant_status")
    diagnostics = _density_match_diagnostics(rows, valid_rows, invalid_rows)
    seed_schedule = _seed_schedule(rows)
    readout_horizon = _common_positive_int(rows, "readout_horizon_steps", config.default_readout_horizon_steps)
    run_id = _common_value(rows, "run_id", "fixture-paired-signal")
    config_id = _common_value(rows, "config_id", "fixture-config")
    protocol_id = _common_value(rows, "protocol_id", "switch-point-test-protocol-v1")

    notes: list[str] = []
    if replay_status != OK_STATUS or invariant_status != OK_STATUS:
        verdict = "invalid_runner"
        notes.append("replay/invariant failure")
    elif invalid_rate > config.invalid_rate_diagnostic_threshold:
        verdict = "diagnostic_only"
        notes.append("invalid-pair rate exceeds 25%")
    elif mean_delta is not None and mean_delta > 0 and (percent_positive or 0.0) > 50.0:
        verdict = "pass_signal"
    else:
        verdict = "mixed_signal"
    if attempted and attempted < config.target_valid_pairs:
        notes.append(
            f"fixture-only contract report: {len(valid_rows)} valid pairs < {config.target_valid_pairs} target valid pairs"
        )
    if attempted and attempted > config.attempted_pair_cap:
        notes.append(f"attempted pairs exceed cap: {attempted} > {config.attempted_pair_cap}")

    return PairedSignalReport(
        rows=rows,
        verdict=verdict,
        evidence_label=EVIDENCE_LABEL_SIGNAL_SMOKE_ONLY,
        valid_pairs=len(valid_rows),
        attempted_pairs=attempted,
        invalid_pairs=len(invalid_rows),
        invalid_rate=invalid_rate,
        mean_burned_area_avoided=mean_delta,
        median_burned_area_avoided=median_delta,
        percent_ranger_avoided_more_burned_area=percent_positive,
        uncertainty_interval=interval,
        density_match_diagnostics=diagnostics,
        replay_status=replay_status,
        runner_invariant_status=invariant_status,
        seed_schedule=seed_schedule,
        readout_horizon_steps=readout_horizon,
        config_id=config_id,
        protocol_id=protocol_id,
        run_id=run_id,
        schema_version=config.schema_version,
        notes=notes,
    )


def write_paired_signal_artifacts(report: PairedSignalReport, out_dir: Path) -> dict[str, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "paired_signal.csv"
    markdown_path = out_dir / "paired_signal_report.md"
    json_path = out_dir / "paired_signal_summary.json"

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PAIRED_SIGNAL_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(report.rows)
    markdown_path.write_text(report.to_markdown(), encoding="utf-8")
    json_path.write_text(json.dumps(report.to_json_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"csv": csv_path, "markdown": markdown_path, "json": json_path}


def build_fixture_signal_rows(valid_pairs: int = 3, invalid_pairs: int = 0) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    total = valid_pairs + invalid_pairs
    for index in range(total):
        valid = index < valid_pairs
        control_burned = 12 + index
        treatment_burned = control_burned - 4 if valid else control_burned
        row = {
            "schema_version": "1",
            "run_id": "fixture-paired-signal",
            "pair_id": f"pair-{index:03d}",
            "seed": str(10_000 + index % 5),
            "episode_id": str(index // 5),
            "timestep": str(200 + index),
            "treatment_row": "2",
            "treatment_col": str(index % 4),
            "treatment_index": str(8 + index),
            "control_row": "3",
            "control_col": str((index + 1) % 4),
            "control_index": str(12 + index),
            "ranger_density_trees_7x7": "18",
            "ranger_density_cells_7x7": "32",
            "ranger_density_tercile": "mid",
            "control_density_trees_7x7": "18" if valid else "",
            "control_density_cells_7x7": "32" if valid else "",
            "control_density_tercile": "mid" if valid else "invalid",
            "match_quality": "exact_tercile" if valid else "no_same_tercile_control",
            "valid_pair": "true" if valid else "false",
            "validity_reason": "ok" if valid else "no_same_tercile_control",
            "treatment_burned_cells": str(treatment_burned),
            "control_burned_cells": str(control_burned),
            "burned_area_avoided_delta": str(control_burned - treatment_burned),
            "treatment_living_tree_fraction": "0.620",
            "control_living_tree_fraction": "0.580",
            "living_tree_fraction_delta": "0.040",
            "readout_horizon_steps": "512",
            "config_id": "fixture-config-v1",
            "protocol_id": "switch-point-test-protocol-v1",
            "runner_invariant_status": "ok",
            "replay_status": "ok",
            "evidence_label": EVIDENCE_LABEL_SIGNAL_SMOKE_ONLY,
        }
        rows.append(row)
    return rows


def _density_match_diagnostics(
    rows: list[dict[str, str]],
    valid_rows: list[dict[str, str]],
    invalid_rows: list[dict[str, str]],
) -> dict[str, Any]:
    exact_count = sum(
        1
        for row in valid_rows
        if row.get("ranger_density_tercile") == row.get("control_density_tercile")
        and row.get("match_quality") == "exact_tercile"
    )
    invalid_reasons: dict[str, int] = {}
    for row in invalid_rows:
        reason = row.get("validity_reason", "unknown") or "unknown"
        invalid_reasons[reason] = invalid_reasons.get(reason, 0) + 1
    qualities = [1.0 for row in valid_rows if row.get("match_quality") == "exact_tercile"]
    return {
        "exact_tercile_match_count": exact_count,
        "valid_pair_count": len(valid_rows),
        "invalid_reasons": invalid_reasons,
        "mean_match_quality": mean(qualities) if qualities else None,
        "all_rows_signal_smoke_only": all(row.get("evidence_label") == EVIDENCE_LABEL_SIGNAL_SMOKE_ONLY for row in rows),
    }


def _seed_schedule(rows: list[dict[str, str]]) -> dict[str, Any]:
    seeds = sorted({_non_negative_int(row["seed"], "seed") for row in rows})
    counts = {str(seed): sum(1 for row in rows if int(row["seed"]) == seed) for seed in seeds}
    return {"seeds": seeds, "pair_count_by_seed": counts}


def _combined_status(rows: list[dict[str, str]], key: str) -> str:
    statuses = [row.get(key, "") for row in rows]
    return OK_STATUS if all(status == OK_STATUS for status in statuses) else "invalid"


def _simple_uncertainty_interval(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"method": "fixture_min_max", "low": None, "high": None}  # type: ignore[dict-item]
    return {"method": "fixture_min_max", "low": min(values), "high": max(values)}  # type: ignore[dict-item]


def _common_value(rows: list[dict[str, str]], key: str, default: str) -> str:
    values = [row.get(key, "") for row in rows if row.get(key, "")]
    return values[0] if values else default


def _common_positive_int(rows: list[dict[str, str]], key: str, default: int) -> int:
    values = [row.get(key, "") for row in rows if row.get(key, "")]
    return _positive_int(values[0], key) if values else default


def _parse_bool(value: str, label: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"{label} must be true or false")


def _parse_float(value: str, label: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be numeric") from exc


def _non_negative_int(value: str, label: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise ValueError(f"{label} must be non-negative")
    return parsed


def _positive_int(value: str, label: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise ValueError(f"{label} must be positive")
    return parsed


def _format_optional_float(value: Any) -> str:
    return "n/a" if value is None else f"{float(value):.3f}"


def _format_optional_percent(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1f}%"
