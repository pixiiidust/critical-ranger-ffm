from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from critical_ranger_ffm.reporting.report_fire_sizes import load_cluster_rows, orders_of_magnitude


@dataclass(frozen=True)
class BaselineGateConfig:
    min_closed_clusters: int = 50
    min_orders_of_magnitude: float = 1.5
    min_tail_fire_size: int = 128
    max_overlap_rate: float = 0.05


@dataclass(frozen=True)
class BaselineGateResult:
    status: str
    recommendation: str
    messages: list[str]
    metrics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_baseline_gates(
    clusters_path: Path,
    summary_json_path: Path | None = None,
    config: BaselineGateConfig | None = None,
) -> BaselineGateResult:
    config = config or BaselineGateConfig()
    rows = [row for row in load_cluster_rows(Path(clusters_path)) if row["mode"] == "baseline"]
    summary = _read_summary(summary_json_path)

    sizes = [int(row["fire_size"]) for row in rows]
    overlap_count = sum(1 for row in rows if row.get("overlap_signal") == "multi_component")
    overlap_rate = _summary_float(summary, "overlap_rate")
    if overlap_rate is None:
        overlap_rate = overlap_count / len(rows) if rows else 0.0

    max_size = max(sizes) if sizes else 0
    orders = orders_of_magnitude(sizes)
    tail_count = sum(1 for size in sizes if size >= config.min_tail_fire_size)

    failures: list[str] = []
    warnings: list[str] = []

    if len(sizes) < config.min_closed_clusters:
        failures.append(
            "too few closed clusters: "
            f"{len(sizes)} observed < {config.min_closed_clusters} required for baseline smoke"
        )
    if sizes and orders < config.min_orders_of_magnitude:
        warnings.append(
            "too-narrow fire-size range: "
            f"{orders:.2f} orders < {config.min_orders_of_magnitude:.2f} target"
        )
    if sizes and tail_count == 0:
        warnings.append(
            "unpopulated tail: "
            f"largest closed fire is {max_size}, below tail threshold {config.min_tail_fire_size}"
        )
    if rows and overlap_rate > config.max_overlap_rate:
        warnings.append(
            "overlap is common: "
            f"{overlap_rate:.3f} observed > {config.max_overlap_rate:.3f} allowed"
        )

    status = "fail" if failures else "warn" if warnings else "pass"
    messages = failures + warnings
    metrics: dict[str, Any] = {
        "cluster_count": len(sizes),
        "fire_size_min": min(sizes) if sizes else None,
        "fire_size_max": max_size if sizes else None,
        "orders_of_magnitude": orders,
        "tail_count": tail_count,
        "overlap_count": overlap_count,
        "overlap_rate": overlap_rate,
        "steps_run": summary.get("steps_run"),
        "config": asdict(config),
    }
    return BaselineGateResult(status, _recommendation(status, failures, warnings), messages, metrics)


def _read_summary(path: Path | None) -> dict[str, Any]:
    if not path:
        return {}
    with Path(path).open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("summary JSON must be an object")
    return data


def _summary_float(summary: dict[str, Any], key: str) -> float | None:
    value = summary.get(key)
    if value is None:
        return None
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"summary {key} must be finite")
    return parsed


def _recommendation(status: str, failures: list[str], warnings: list[str]) -> str:
    text = " ".join(failures + warnings).lower()
    if status == "pass":
        return "Baseline smoke gates passed; move to measurement runs."
    actions: list[str] = []
    if "too few closed clusters" in text:
        actions.append("run longer")
    if "too-narrow" in text or "unpopulated tail" in text:
        actions.append("tune p or tune f to populate the fire-size tail")
    if "overlap is common" in text:
        actions.append("tune f downward or increase the quiet window before trusting cluster closures")
    if not actions:
        actions.append("inspect the unmanaged smoke output before measurement runs")
    return f"Baseline smoke gates {status}; " + "; ".join(actions) + "."


def format_text(result: BaselineGateResult) -> str:
    lines = [f"status={result.status}", f"recommendation={result.recommendation}", "metrics:"]
    for key, value in result.metrics.items():
        if key == "config":
            continue
        lines.append(f"  {key}: {value}")
    if result.messages:
        lines.append("messages:")
        for message in result.messages:
            prefix = "FAIL" if result.status == "fail" and message == result.messages[0] else "WARN"
            lines.append(f"  {prefix}: {message}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate unmanaged FFM baseline smoke gates")
    parser.add_argument("--clusters", required=True, type=Path)
    parser.add_argument("--summary-json", type=Path)
    parser.add_argument("--min-closed-clusters", type=int, default=BaselineGateConfig.min_closed_clusters)
    parser.add_argument("--min-orders-of-magnitude", type=float, default=BaselineGateConfig.min_orders_of_magnitude)
    parser.add_argument("--min-tail-fire-size", type=int, default=BaselineGateConfig.min_tail_fire_size)
    parser.add_argument("--max-overlap-rate", type=float, default=BaselineGateConfig.max_overlap_rate)
    parser.add_argument("--json", action="store_true", help="print machine-readable gate result")
    args = parser.parse_args(argv)

    config = BaselineGateConfig(
        min_closed_clusters=args.min_closed_clusters,
        min_orders_of_magnitude=args.min_orders_of_magnitude,
        min_tail_fire_size=args.min_tail_fire_size,
        max_overlap_rate=args.max_overlap_rate,
    )
    result = evaluate_baseline_gates(args.clusters, args.summary_json, config)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        print(format_text(result))
    return 0 if result.status in {"pass", "warn"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
