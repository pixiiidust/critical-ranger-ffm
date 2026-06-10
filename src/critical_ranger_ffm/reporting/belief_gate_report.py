from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, median
from typing import Any, cast

from critical_ranger_ffm.reporting.paired_signal_report import (
    PAIRED_SIGNAL_CSV_COLUMNS,
    PairedSignalConfig,
    evaluate_paired_signal_report,
)

VALID_BELIEF_GATE_VERDICTS = {"pass_belief_gate", "mixed_belief_gate", "diagnostic_only", "invalid_runner"}
EVIDENCE_LABEL_PROVISIONAL_BELIEF_GATE = "provisional_belief_gate"
OK_STATUS = "ok"


@dataclass(frozen=True)
class BeliefGateConfig:
    target_valid_pairs: int = 500
    attempted_pair_cap: int = 750
    min_independent_seeds: int = 50
    max_valid_pairs_per_seed: int = 10
    max_seed_share: float = 0.05
    invalid_rate_diagnostic_threshold: float = 0.25
    default_readout_horizon_steps: int = 512
    schema_version: str = "1"


@dataclass(frozen=True)
class BeliefGateReport:
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
    seed_distribution: dict[str, Any]
    seed_stratified_burned_area_avoided: dict[str, dict[str, float | int | None]]
    seed_count: int
    max_valid_pairs_per_seed: int
    max_seed_share: float
    replay_status: str
    runner_invariant_status: str
    readout_horizon_steps: int
    config_id: str
    protocol_id: str
    run_id: str
    schema_version: str = "1"
    notes: list[str] = field(default_factory=list)

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
            "seed_distribution": self.seed_distribution,
            "seed_stratified_burned_area_avoided": self.seed_stratified_burned_area_avoided,
            "seed_count": self.seed_count,
            "max_valid_pairs_per_seed": self.max_valid_pairs_per_seed,
            "max_seed_share": self.max_seed_share,
            "replay_status": self.replay_status,
            "runner_invariant_status": self.runner_invariant_status,
            "readout_horizon_steps": self.readout_horizon_steps,
            "config_id": self.config_id,
            "protocol_id": self.protocol_id,
            "notes": self.notes,
        }

    def to_markdown(self) -> str:
        mean_value = _format_optional_float(self.mean_burned_area_avoided)
        median_value = _format_optional_float(self.median_burned_area_avoided)
        pct_value = _format_optional_percent(self.percent_ranger_avoided_more_burned_area)
        lo = _format_optional_float(self.uncertainty_interval.get("low"))
        hi = _format_optional_float(self.uncertainty_interval.get("high"))
        seed_lines = [
            f"- {seed}: count={stats['valid_pairs']}, mean={_format_optional_float(stats['mean_burned_area_avoided'])}"
            for seed, stats in sorted(self.seed_stratified_burned_area_avoided.items(), key=lambda item: int(item[0]))
        ]
        if not seed_lines:
            seed_lines = ["- none"]
        notes = "\n".join(f"- {note}" for note in self.notes) if self.notes else "- none"
        return "\n".join(
            [
                "# 500-valid-pair belief gate report",
                "",
                f"Verdict: `{self.verdict}`",
                f"Evidence label: `{self.evidence_label}`",
                "",
                "Passing this gate supports provisional ranger-efficacy belief only.",
                "It is not final criticality, SOC control, publication-grade science, or policy quality.",
                "",
                "## Required metrics",
                "",
                f"- Valid pairs: {self.valid_pairs}",
                f"- Attempted pairs: {self.attempted_pairs}",
                f"- Invalid pairs: {self.invalid_pairs}",
                f"- Invalid rate: {self.invalid_rate:.1%}",
                f"- Mean burned-area avoided: {mean_value}",
                f"- Median burned-area avoided: {median_value}",
                f"- Ranger avoided more burned area: {pct_value}",
                f"- Uncertainty interval: [{lo}, {hi}]",
                f"- Independent seeds: {self.seed_count}",
                f"- Max valid pairs per seed: {self.max_valid_pairs_per_seed}",
                f"- Max seed share: {self.max_seed_share:.1%}",
                f"- Replay status: `{self.replay_status}`",
                f"- Runner invariant status: `{self.runner_invariant_status}`",
                f"- Read-out horizon: {self.readout_horizon_steps} steps",
                "",
                "## Density-match diagnostics",
                "",
                f"- Exact tercile matches: {self.density_match_diagnostics.get('exact_tercile_match_count', 0)}",
                f"- Valid match-quality mean: {_format_optional_float(self.density_match_diagnostics.get('mean_match_quality'))}",
                f"- Invalid reasons: {self.density_match_diagnostics.get('invalid_reasons', {})}",
                "",
                "## seed-stratified burned-area avoided",
                "",
                *seed_lines,
                "",
                "## Notes",
                "",
                notes,
            ]
        )


def evaluate_belief_gate_report(
    rows: list[dict[str, str]],
    config: BeliefGateConfig | None = None,
) -> BeliefGateReport:
    config = config or BeliefGateConfig()
    signal = evaluate_paired_signal_report(
        rows,
        PairedSignalConfig(
            invalid_rate_diagnostic_threshold=config.invalid_rate_diagnostic_threshold,
            target_valid_pairs=config.target_valid_pairs,
            attempted_pair_cap=config.attempted_pair_cap,
            default_readout_horizon_steps=config.default_readout_horizon_steps,
            schema_version=config.schema_version,
        ),
    )
    valid_rows = [row for row in rows if _parse_bool(row["valid_pair"])]
    seed_stats = _seed_stratified_burned_area_avoided(valid_rows)
    seed_count = len(seed_stats)
    max_pairs = max((cast(int, stats["valid_pairs"]) for stats in seed_stats.values()), default=0)
    max_share = (max_pairs / len(valid_rows)) if valid_rows else 0.0
    notes = list(signal.notes)

    if signal.replay_status != OK_STATUS or signal.runner_invariant_status != OK_STATUS:
        verdict = "invalid_runner"
        if "replay/invariant failure" not in notes:
            notes.append("replay/invariant failure")
    else:
        if signal.valid_pairs < config.target_valid_pairs:
            notes.append("valid pairs below belief-gate threshold")
        if signal.attempted_pairs > config.attempted_pair_cap:
            notes.append("attempted pairs exceed cap")
        if signal.invalid_rate > config.invalid_rate_diagnostic_threshold:
            notes.append("invalid-pair rate exceeds 25%")
        if seed_count < config.min_independent_seeds:
            notes.append("independent seed count below threshold")
        if max_pairs > config.max_valid_pairs_per_seed:
            notes.append("seed contribution exceeds max valid pairs per seed")
        if max_share > config.max_seed_share:
            notes.append("seed contribution exceeds max share")

        threshold_failure_notes = {
            "valid pairs below belief-gate threshold",
            "attempted pairs exceed cap",
            "invalid-pair rate exceeds 25%",
            "independent seed count below threshold",
            "seed contribution exceeds max valid pairs per seed",
            "seed contribution exceeds max share",
        }
        if any(note in threshold_failure_notes for note in notes):
            verdict = "diagnostic_only"
        elif signal.mean_burned_area_avoided is not None and signal.mean_burned_area_avoided > 0 and (
            signal.percent_ranger_avoided_more_burned_area or 0.0
        ) > 50.0:
            verdict = "pass_belief_gate"
        else:
            verdict = "mixed_belief_gate"

    return BeliefGateReport(
        rows=rows,
        verdict=verdict,
        evidence_label=EVIDENCE_LABEL_PROVISIONAL_BELIEF_GATE,
        valid_pairs=signal.valid_pairs,
        attempted_pairs=signal.attempted_pairs,
        invalid_pairs=signal.invalid_pairs,
        invalid_rate=signal.invalid_rate,
        mean_burned_area_avoided=signal.mean_burned_area_avoided,
        median_burned_area_avoided=signal.median_burned_area_avoided,
        percent_ranger_avoided_more_burned_area=signal.percent_ranger_avoided_more_burned_area,
        uncertainty_interval=signal.uncertainty_interval,
        density_match_diagnostics=signal.density_match_diagnostics,
        seed_distribution=signal.seed_schedule,
        seed_stratified_burned_area_avoided=seed_stats,
        seed_count=seed_count,
        max_valid_pairs_per_seed=max_pairs,
        max_seed_share=max_share,
        replay_status=signal.replay_status,
        runner_invariant_status=signal.runner_invariant_status,
        readout_horizon_steps=signal.readout_horizon_steps,
        config_id=signal.config_id,
        protocol_id=signal.protocol_id,
        run_id=signal.run_id,
        schema_version=signal.schema_version,
        notes=notes,
    )


def write_belief_gate_artifacts(rows: list[dict[str, str]], out_dir: Path, config: BeliefGateConfig | None = None) -> dict[str, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = evaluate_belief_gate_report(rows, config)
    csv_path = out_dir / "paired_signal.csv"
    markdown_path = out_dir / "belief_gate_report.md"
    json_path = out_dir / "belief_gate_summary.json"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PAIRED_SIGNAL_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    markdown_path.write_text(report.to_markdown(), encoding="utf-8")
    json_path.write_text(json.dumps(report.to_json_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"csv": csv_path, "markdown": markdown_path, "json": json_path}


def _seed_stratified_burned_area_avoided(rows: list[dict[str, str]]) -> dict[str, dict[str, float | int | None]]:
    grouped: dict[str, list[float]] = {}
    for row in rows:
        grouped.setdefault(row["seed"], []).append(_parse_float(row["burned_area_avoided_delta"]))
    stats: dict[str, dict[str, float | int | None]] = {}
    for seed, values in grouped.items():
        stats[seed] = {
            "valid_pairs": len(values),
            "mean_burned_area_avoided": mean(values) if values else None,
            "median_burned_area_avoided": median(values) if values else None,
            "positive_pair_percent": (100.0 * sum(1 for value in values if value > 0) / len(values)) if values else None,
        }
    return stats


def _parse_bool(text: str) -> bool:
    lowered = text.strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    raise ValueError(f"expected boolean text, got {text!r}")


def _parse_float(text: str) -> float:
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"expected float text, got {text!r}") from exc


def _format_optional_float(value: float | int | None) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.3f}"


def _format_optional_percent(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f}%"
