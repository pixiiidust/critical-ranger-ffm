from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from statistics import mean, pstdev
from typing import Iterable

from critical_ranger_ffm.reporting.report_fire_sizes import fit_slope, orders_of_magnitude

FROZEN_ARENA_KEYS = [
    "grid_width",
    "grid_height",
    "min_gate_grid_size",
    "connectivity",
    "p",
    "f",
    "warmup_steps",
]

DEFAULT_REPEATABILITY_THRESHOLDS = {
    "density_max_range": 0.01,
    "slope_max_range": 0.08,
    "min_orders_of_magnitude": 1.5,
    "max_overlap_rate": 0.10,
}


def load_ini_config(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def compare_arena_constants(frozen_path: Path, candidate_path: Path) -> list[str]:
    frozen = load_ini_config(frozen_path)
    candidate = load_ini_config(candidate_path)
    mismatches: list[str] = []
    for key in FROZEN_ARENA_KEYS:
        expected = frozen.get(key)
        actual = candidate.get(key)
        if expected != actual:
            mismatches.append(f"{key}: expected {expected!r}, got {actual!r}")
    return mismatches


def _read_cluster_sizes(csv_path: Path) -> list[int]:
    with Path(csv_path).open(newline="", encoding="utf-8") as handle:
        return [int(row["fire_size"]) for row in csv.DictReader(handle)]


def compute_seed_summary(csv_path: Path, summary_json_path: Path) -> dict[str, object]:
    sizes = _read_cluster_sizes(csv_path)
    summary = json.loads(Path(summary_json_path).read_text(encoding="utf-8"))
    slope = fit_slope(sizes)
    result = {
        "seed": summary.get("seed"),
        "cluster_count": len(sizes),
        "fire_size_min": min(sizes) if sizes else 0,
        "fire_size_max": max(sizes) if sizes else 0,
        "orders_of_magnitude": orders_of_magnitude(sizes),
        "fitted_slope": slope,
        "critical_density_mean": summary.get("critical_density_mean"),
        "critical_density_band_min": summary.get("critical_density_band_min"),
        "critical_density_band_max": summary.get("critical_density_band_max"),
        "multi_component_window_rate": summary.get("multi_component_window_rate"),
        "steps_run": summary.get("steps_run"),
        "measurement_grid_gate": summary.get("measurement_grid_gate"),
        "sample_size_gate": summary.get("sample_size_gate"),
        "size_range_gate": summary.get("size_range_gate"),
        "overlap_gate": summary.get("overlap_gate"),
        "critical_density_gate": summary.get("critical_density_gate"),
        "heavy_tail_gate": summary.get("heavy_tail_gate"),
        "csv": str(csv_path),
        "summary": str(summary_json_path),
    }
    return result


def _numeric_values(seed_summaries: Iterable[dict[str, object]], key: str) -> list[float]:
    values: list[float] = []
    for summary in seed_summaries:
        value = summary.get(key)
        if value is None or value == "":
            continue
        values.append(float(value))
    return values


def _range(values: list[float]) -> float:
    return max(values) - min(values) if values else 0.0


def evaluate_repeatability(seed_summaries: list[dict[str, object]], thresholds: dict[str, float]) -> dict[str, object]:
    thresholds = {**DEFAULT_REPEATABILITY_THRESHOLDS, **thresholds}
    density_values = _numeric_values(seed_summaries, "critical_density_mean")
    slope_values = _numeric_values(seed_summaries, "fitted_slope")
    order_values = _numeric_values(seed_summaries, "orders_of_magnitude")
    overlap_values = _numeric_values(seed_summaries, "multi_component_window_rate")

    density_range = _range(density_values)
    slope_range = _range(slope_values)
    min_orders = min(order_values) if order_values else 0.0
    max_overlap = max(overlap_values) if overlap_values else 1.0

    density_pass = bool(density_values) and density_range <= thresholds["density_max_range"]
    slope_pass = bool(slope_values) and slope_range <= thresholds["slope_max_range"]
    heavy_tail_pass = all(summary.get("heavy_tail_gate") == "pass" for summary in seed_summaries)
    order_pass = bool(order_values) and min_orders >= thresholds["min_orders_of_magnitude"]
    overlap_pass = bool(overlap_values) and max_overlap <= thresholds["max_overlap_rate"]

    gate = "pass" if density_pass and slope_pass and heavy_tail_pass and order_pass and overlap_pass else "fail"
    return {
        "repeatability_gate": gate,
        "seed_count": len(seed_summaries),
        "thresholds": thresholds,
        "density_mean": mean(density_values) if density_values else None,
        "density_stddev": pstdev(density_values) if len(density_values) > 1 else 0.0,
        "density_range": density_range,
        "density_repeatability_pass": density_pass,
        "slope_mean": mean(slope_values) if slope_values else None,
        "slope_stddev": pstdev(slope_values) if len(slope_values) > 1 else 0.0,
        "slope_range": slope_range,
        "slope_repeatability_pass": slope_pass,
        "min_orders_of_magnitude": min_orders,
        "orders_gate_pass": order_pass,
        "max_multi_component_window_rate": max_overlap,
        "overlap_gate_pass": overlap_pass,
        "heavy_tail_gate_pass": heavy_tail_pass,
        "seeds": seed_summaries,
    }


def _compile_demo(demo_source: Path, binary_path: Path) -> None:
    completed = subprocess.run(
        ["cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-pedantic", str(demo_source), "-lm", "-o", str(binary_path)],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr + completed.stdout)


def run_repeatability_sweep(
    demo_source: Path,
    config_path: Path,
    out_dir: Path,
    seeds: list[int],
    overrides: dict[str, str] | None = None,
    thresholds: dict[str, float] | None = None,
) -> dict[str, object]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    thresholds = dict(DEFAULT_REPEATABILITY_THRESHOLDS if thresholds is None else thresholds)
    overrides = overrides or {}

    with tempfile.TemporaryDirectory() as tmp_dir:
        binary = Path(tmp_dir) / "ffm_baseline_smoke"
        _compile_demo(Path(demo_source), binary)
        seed_summaries = []
        for seed in seeds:
            seed_dir = out_dir / f"seed-{seed}"
            seed_dir.mkdir(parents=True, exist_ok=True)
            csv_path = seed_dir / "clusters.csv"
            summary_path = seed_dir / "summary.json"
            command = [
                str(binary),
                "--config",
                str(config_path),
                "--seed",
                str(seed),
                "--out",
                str(csv_path),
                "--summary",
                str(summary_path),
            ]
            for key, value in sorted(overrides.items()):
                command.extend([f"--{key.replace('_', '-')}", str(value)])
            completed = subprocess.run(command, text=True, capture_output=True, check=False)
            if completed.returncode != 0:
                raise RuntimeError(completed.stderr + completed.stdout)
            (seed_dir / "stdout.txt").write_text(completed.stdout, encoding="utf-8")
            seed_summaries.append(compute_seed_summary(csv_path, summary_path))

    result = evaluate_repeatability(seed_summaries, thresholds)
    result["config"] = str(config_path)
    result["demo_source"] = str(demo_source)
    result["out_dir"] = str(out_dir)
    (out_dir / "repeatability_summary.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Part C0.1 baseline repeatability seed sweep")
    parser.add_argument("--demo-source", type=Path, default=Path("demos/ffm_baseline_smoke.c"))
    parser.add_argument("--config", type=Path, default=Path("configs/ffm_baseline_smoke.ini"))
    parser.add_argument("--out-dir", type=Path, default=Path("reports/part-c0-1-repeatability"))
    parser.add_argument("--seeds", default="20260609,20260610,20260611")
    parser.add_argument("--density-max-range", type=float, default=DEFAULT_REPEATABILITY_THRESHOLDS["density_max_range"])
    parser.add_argument("--slope-max-range", type=float, default=DEFAULT_REPEATABILITY_THRESHOLDS["slope_max_range"])
    args = parser.parse_args(argv)

    thresholds = dict(DEFAULT_REPEATABILITY_THRESHOLDS)
    thresholds["density_max_range"] = args.density_max_range
    thresholds["slope_max_range"] = args.slope_max_range
    seeds = [int(seed.strip()) for seed in args.seeds.split(",") if seed.strip()]
    result = run_repeatability_sweep(args.demo_source, args.config, args.out_dir, seeds, thresholds=thresholds)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["repeatability_gate"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
