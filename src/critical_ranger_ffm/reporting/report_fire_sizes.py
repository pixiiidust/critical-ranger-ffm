from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path
from statistics import mean, pstdev
from typing import Iterable

VALID_CLUSTER_MODES = {
    "baseline",
    "agent",
    "ranger_intervention",
    "density_matched_control",
}
VALID_INTERVENTION_MODES = {"ranger_intervention", "density_matched_control"}
VALID_CELL_STATES = {"empty", "tree", "burning"}

REQUIRED_CLUSTER_COLUMNS = [
    "schema_version",
    "run_id",
    "mode",
    "seed",
    "episode_id",
    "step",
    "event_id",
    "cluster_id",
    "fire_size",
    "grid_width",
    "grid_height",
    "p",
    "f",
    "global_tree_density",
    "quiet_window_component_count",
    "overlap_signal",
    "pair_id",
    "source",
    "notes",
]

REQUIRED_INTERVENTION_COLUMNS = [
    "schema_version",
    "pair_id",
    "run_id",
    "mode",
    "seed",
    "episode_id",
    "intervention_step",
    "action_row",
    "action_col",
    "selected_cell_state",
    "effective_intervention",
    "local_fuel_density",
    "density_bucket",
    "matched_control_for_pair_id",
    "post_intervention_seed",
    "downstream_window_steps",
    "source",
    "notes",
]


@dataclass(frozen=True)
class ReportingConfig:
    min_clusters_for_fit: int = 50
    min_orders_of_magnitude: float = 1.5
    steps_window_size: int = 10_000
    consecutive_windows_required: int = 3
    slope_band_min: float | None = None
    slope_band_max: float | None = None
    baseline_slope_band_half_width: float = 0.25
    filter_non_effective_interventions: bool = True
    provisional_results: bool = True


@dataclass(frozen=True)
class ReportResult:
    summary_table: str
    warnings: list[str]
    output_files: list[Path]


def _read_csv(path: Path, required: list[str], label: str) -> list[dict[str, str]]:
    path = Path(path)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        missing = [column for column in required if column not in fieldnames]
        if missing:
            raise ValueError(f"missing required {label} columns: {', '.join(missing)}")
        return list(reader)


def load_cluster_rows(path: Path) -> list[dict[str, str]]:
    rows = _read_csv(Path(path), REQUIRED_CLUSTER_COLUMNS, "cluster")
    for index, row in enumerate(rows, start=2):
        mode = row["mode"]
        if mode not in VALID_CLUSTER_MODES:
            raise ValueError(f"unknown cluster mode on line {index}: {mode}")
        _positive_int(row["fire_size"], f"fire_size on line {index}")
        _non_negative_int(row["step"], f"step on line {index}")
    return rows


def load_intervention_rows(path: Path) -> list[dict[str, str]]:
    rows = _read_csv(Path(path), REQUIRED_INTERVENTION_COLUMNS, "intervention")
    for index, row in enumerate(rows, start=2):
        mode = row["mode"]
        if mode not in VALID_INTERVENTION_MODES:
            raise ValueError(f"unknown intervention mode on line {index}: {mode}")
        if row["selected_cell_state"] not in VALID_CELL_STATES:
            raise ValueError(f"unknown selected_cell_state on line {index}: {row['selected_cell_state']}")
        _parse_bool(row["effective_intervention"], f"effective_intervention on line {index}")
    validate_pairing_contract(rows, ReportingConfig())
    return rows


def validate_pairing_contract(rows: list[dict[str, str]], config: ReportingConfig) -> list[str]:
    warnings: list[str] = []
    by_pair: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)

    for row in rows:
        effective = _parse_bool(row["effective_intervention"], "effective_intervention")
        selected_state = row["selected_cell_state"]
        mode = row["mode"]
        pair_id = row["pair_id"]

        if effective and selected_state != "tree":
            raise ValueError("effective_intervention=true requires selected_cell_state=tree")
        if not effective and selected_state == "tree":
            raise ValueError("selected_cell_state=tree must use effective_intervention=true")
        if not effective:
            action = "excluded" if config.filter_non_effective_interventions else "flagged"
            warnings.append(f"non-effective intervention {action}: pair_id={pair_id} mode={mode}")
        if pair_id:
            by_pair[pair_id][mode] = row

    for pair_id, modes in sorted(by_pair.items()):
        ranger = modes.get("ranger_intervention")
        control = modes.get("density_matched_control")
        if not ranger or not control:
            warnings.append(f"incomplete intervention pair: pair_id={pair_id}")
            continue
        if ranger["density_bucket"] != control["density_bucket"]:
            warnings.append(
                "density bucket mismatch: "
                f"pair_id={pair_id} ranger={ranger['density_bucket']} control={control['density_bucket']}"
            )
        if ranger.get("post_intervention_seed") != control.get("post_intervention_seed"):
            warnings.append(f"post-intervention seed mismatch: pair_id={pair_id}")
    return warnings


def write_report(
    clusters_path: Path,
    interventions_path: Path,
    out_dir: Path,
    config_path: Path | None = None,
) -> ReportResult:
    config = load_config(config_path) if config_path else ReportingConfig()
    clusters = load_cluster_rows(Path(clusters_path))
    interventions = load_intervention_rows(Path(interventions_path))
    warnings = validate_pairing_contract(interventions, config)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    summaries, summary_warnings = summarize_modes(clusters, config)
    warnings.extend(summary_warnings)

    fire_plot = out_dir / "fire_size_loglog.png"
    shift_plot = out_dir / "intervention_shift.png"
    plot_fire_size_distribution(clusters, summaries, fire_plot, warnings)
    plot_intervention_shift(clusters, interventions, shift_plot, config, warnings)

    table = format_summary_table(summaries)
    return ReportResult(table, warnings, [fire_plot, shift_plot])


def load_config(path: Path | None) -> ReportingConfig:
    if not path:
        return ReportingConfig()
    with Path(path).open(encoding="utf-8") as handle:
        data = json.load(handle)
    config = ReportingConfig()
    allowed = set(config.__dataclass_fields__.keys())
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ValueError(f"unknown reporting config keys: {', '.join(unknown)}")
    return replace(config, **data)


def summarize_modes(rows: list[dict[str, str]], config: ReportingConfig) -> tuple[list[dict[str, object]], list[str]]:
    warnings: list[str] = []
    summaries: list[dict[str, object]] = []
    by_mode: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_mode[row["mode"]].append(row)

    baseline_slope = None
    baseline_rows = by_mode.get("baseline", [])
    if baseline_rows:
        baseline_slope = fit_slope([int(row["fire_size"]) for row in baseline_rows])

    for mode in ["baseline", "agent", "ranger_intervention", "density_matched_control"]:
        mode_rows = by_mode.get(mode, [])
        sizes = [int(row["fire_size"]) for row in mode_rows]
        slope = fit_slope(sizes) if len(sizes) >= 2 else None
        orders = orders_of_magnitude(sizes)
        mode_warnings = []
        if not mode_rows:
            mode_warnings.append(f"no {mode} rows found")
        if len(sizes) < config.min_clusters_for_fit:
            mode_warnings.append(
                f"small sample for {mode}: {len(sizes)} clusters < {config.min_clusters_for_fit}; slope provisional"
            )
        if sizes and orders < config.min_orders_of_magnitude:
            mode_warnings.append(
                f"narrow fire-size range for {mode}: {orders:.2f} orders < {config.min_orders_of_magnitude}"
            )
        warnings.extend(mode_warnings)
        summaries.append(
            {
                "mode": mode,
                "cluster_count": len(sizes),
                "fire_size_min": min(sizes) if sizes else "",
                "fire_size_max": max(sizes) if sizes else "",
                "orders_of_magnitude": orders if sizes else "",
                "fitted_slope": slope if slope is not None else "",
                "slope_status": slope_status(slope, baseline_slope, config) if sizes else "missing",
                "steps_to_critical_like": steps_to_critical_like(mode_rows, config, baseline_slope),
                "warning": "; ".join(mode_warnings),
            }
        )
    return summaries, warnings


def fit_slope(sizes: Iterable[int]) -> float | None:
    counts: dict[int, int] = defaultdict(int)
    for size in sizes:
        if size > 0:
            counts[int(size)] += 1
    if len(counts) < 2:
        return None
    xs = [math.log10(size) for size in counts]
    ys = [math.log10(count) for count in counts.values()]
    x_bar = mean(xs)
    y_bar = mean(ys)
    denom = sum((x - x_bar) ** 2 for x in xs)
    if denom == 0:
        return None
    return sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, ys)) / denom


def orders_of_magnitude(sizes: list[int]) -> float:
    positives = [size for size in sizes if size > 0]
    if not positives:
        return 0.0
    low = min(positives)
    high = max(positives)
    if low <= 0 or high <= 0:
        return 0.0
    return math.log10(high / low) if high >= low else 0.0


def slope_status(slope: float | None, baseline_slope: float | None, config: ReportingConfig) -> str:
    if slope is None:
        return "missing"
    lo, hi = slope_band(config, baseline_slope)
    if lo is None or hi is None:
        return "provisional:no-band"
    return "inside-provisional-band" if lo <= slope <= hi else "outside-provisional-band"


def slope_band(config: ReportingConfig, baseline_slope: float | None) -> tuple[float | None, float | None]:
    if config.slope_band_min is not None and config.slope_band_max is not None:
        return config.slope_band_min, config.slope_band_max
    if baseline_slope is None:
        return None, None
    return (
        baseline_slope - config.baseline_slope_band_half_width,
        baseline_slope + config.baseline_slope_band_half_width,
    )


def steps_to_critical_like(rows: list[dict[str, str]], config: ReportingConfig, baseline_slope: float | None) -> str:
    if not rows:
        return ""
    lo, hi = slope_band(config, baseline_slope)
    if lo is None or hi is None:
        return "provisional:no-baseline-band"

    sorted_rows = sorted(rows, key=lambda row: int(row["step"]))
    max_step = int(sorted_rows[-1]["step"])
    consecutive = 0
    for window_end in range(config.steps_window_size, max_step + config.steps_window_size, config.steps_window_size):
        window_rows = [row for row in sorted_rows if int(row["step"]) <= window_end]
        sizes = [int(row["fire_size"]) for row in window_rows]
        slope = fit_slope(sizes)
        stable = (
            len(sizes) >= config.min_clusters_for_fit
            and orders_of_magnitude(sizes) >= config.min_orders_of_magnitude
            and slope is not None
            and lo <= slope <= hi
        )
        consecutive = consecutive + 1 if stable else 0
        if consecutive >= config.consecutive_windows_required:
            return f"{window_end} (provisional)"
    return "not reached (provisional)"


def plot_fire_size_distribution(
    rows: list[dict[str, str]], summaries: list[dict[str, object]], path: Path, warnings: list[str]
) -> None:
    plt = _load_matplotlib()
    by_mode: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        by_mode[row["mode"]].append(int(row["fire_size"]))

    fig, ax = plt.subplots(figsize=(8, 5))
    for mode in ["baseline", "agent"]:
        sizes = by_mode.get(mode, [])
        if not sizes:
            warnings.append(f"no {mode} rows found; skipping {mode} log-log overlay")
            continue
        counts: dict[int, int] = defaultdict(int)
        for size in sizes:
            counts[size] += 1
        xs = sorted(counts)
        ys = [counts[x] for x in xs]
        ax.loglog(xs, ys, marker="o", linestyle="-", label=mode)
    ax.set_xlabel("fire size (closed cluster cells)")
    ax.set_ylabel("count")
    ax.set_title("Fire-size distribution (Part B fixture/report contract)")
    ax.legend()
    ax.grid(True, which="both", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_intervention_shift(
    rows: list[dict[str, str]],
    interventions: list[dict[str, str]],
    path: Path,
    config: ReportingConfig,
    warnings: list[str],
) -> None:
    plt = _load_matplotlib()
    valid_pairs = effective_matched_pairs(interventions, config, warnings)
    pair_modes: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        pair_id = row.get("pair_id", "")
        if pair_id in valid_pairs and row["mode"] in VALID_INTERVENTION_MODES:
            pair_modes[pair_id][row["mode"]].append(int(row["fire_size"]))

    shifts = []
    for pair_id, modes in pair_modes.items():
        ranger_sizes = modes.get("ranger_intervention", [])
        control_sizes = modes.get("density_matched_control", [])
        if ranger_sizes and control_sizes:
            shifts.append(mean(ranger_sizes) - mean(control_sizes))

    fig, ax = plt.subplots(figsize=(7, 5))
    if not shifts:
        warnings.append("no paired intervention rows available for shift plot; writing placeholder")
        ax.text(0.5, 0.5, "No valid paired intervention rows", ha="center", va="center")
        ax.set_axis_off()
    else:
        spread = pstdev(shifts) if len(shifts) > 1 else 0.0
        ax.bar(["ranger - matched control"], [mean(shifts)], yerr=[spread], capsize=8)
        ax.axhline(0, color="black", linewidth=1)
        ax.set_ylabel("downstream mean fire-size shift")
        ax.set_title("Density-matched intervention shift")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def effective_matched_pairs(
    interventions: list[dict[str, str]], config: ReportingConfig, warnings: list[str]
) -> set[str]:
    pair_contract_warnings = validate_pairing_contract(interventions, config)
    warnings.extend(pair_contract_warnings)
    by_pair: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in interventions:
        if row.get("pair_id"):
            by_pair[row["pair_id"]][row["mode"]] = row
    valid = set()
    for pair_id, modes in by_pair.items():
        ranger = modes.get("ranger_intervention")
        control = modes.get("density_matched_control")
        if not ranger or not control:
            continue
        if ranger["density_bucket"] != control["density_bucket"]:
            continue
        if config.filter_non_effective_interventions and (
            not _parse_bool(ranger["effective_intervention"], "effective_intervention")
            or not _parse_bool(control["effective_intervention"], "effective_intervention")
        ):
            continue
        valid.add(pair_id)
    return valid


def format_summary_table(summaries: list[dict[str, object]]) -> str:
    headers = [
        "mode",
        "cluster_count",
        "fire_size_min",
        "fire_size_max",
        "orders_of_magnitude",
        "fitted_slope",
        "slope_status",
        "steps_to_critical_like",
    ]
    lines = [" | ".join(headers)]
    lines.append(" | ".join("-" * len(header) for header in headers))
    for summary in summaries:
        values = []
        for header in headers:
            value = summary[header]
            if isinstance(value, float):
                values.append(f"{value:.3f}")
            else:
                values.append(str(value))
        lines.append(" | ".join(values))
    return "\n".join(lines)


def _positive_int(value: str, label: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise ValueError(f"{label} must be positive")
    return parsed


def _non_negative_int(value: str, label: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise ValueError(f"{label} must be non-negative")
    return parsed


def _parse_bool(value: str, label: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"{label} must be true or false")


def _load_matplotlib():
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        return plt
    except ModuleNotFoundError as exc:
        raise RuntimeError("matplotlib is required for reporting plots") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Critical Ranger FFM Part B reporting smoke script")
    parser.add_argument("--clusters", required=True, type=Path)
    parser.add_argument("--interventions", required=True, type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)

    result = write_report(args.clusters, args.interventions, args.out_dir, args.config)
    print(result.summary_table)
    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"WARNING: {warning}")
    print("\nOutputs:")
    for output_file in result.output_files:
        print(output_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
