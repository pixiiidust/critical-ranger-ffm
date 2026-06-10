from __future__ import annotations

import argparse
import importlib
import json
import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, cast

from critical_ranger_ffm.reporting.paired_switch_point_runner import (
    PairedSwitchPointConfig,
    SwitchPointSample,
    write_paired_switch_point_artifacts,
)

FIXTURE_PROVIDER_MARKERS = ("fixture", "build_fixture_signal_rows")
VALID_VERDICTS = {"pass_signal", "mixed_signal", "diagnostic_only", "invalid_runner"}


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if _looks_like_fixture_provider(args.sample_provider):
            raise ValueError("fixture sample providers are not valid #38 evidence")
        provider = _load_provider(args.sample_provider, args.provider_root)
        samples = list(
            provider(
                target_valid_pairs=args.target_valid_pairs,
                attempted_pair_cap=args.attempted_pair_cap,
                readout_horizon_steps=args.readout_horizon_steps,
                seed_start=args.seed_start,
            )
        )
        _validate_samples(samples)
        config = PairedSwitchPointConfig(
            readout_horizon_steps=args.readout_horizon_steps,
            target_valid_pairs=args.target_valid_pairs,
            attempted_pair_cap=args.attempted_pair_cap,
            run_id=args.run_id,
            config_id=args.config_id,
        )
        artifacts = write_paired_switch_point_artifacts(samples, Path(args.output_dir), config)
        summary = json.loads(artifacts["json"].read_text(encoding="utf-8"))
        _validate_summary(summary)
        _print_review_summary(artifacts, summary)
        return 0
    except Exception as exc:  # pragma: no cover - exercised through subprocess contract tests.
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m critical_ranger_ffm.reporting.local_wsl_paired_signal_check",
        description="Local WSL #38 paired signal/smoke bridge. Requires a real local sample provider.",
    )
    parser.add_argument("--sample-provider", required=True, help="Import path MODULE:CALLABLE returning SwitchPointSample rows.")
    parser.add_argument("--provider-root", default=".", help="Directory prepended to sys.path before loading the provider.")
    parser.add_argument("--output-dir", required=True, help="Directory for paired CSV, Markdown report, and JSON summary.")
    parser.add_argument("--target-valid-pairs", type=int, default=100)
    parser.add_argument("--attempted-pair-cap", type=int, default=150)
    parser.add_argument("--readout-horizon-steps", type=int, default=512)
    parser.add_argument("--seed-start", type=int, default=3701)
    parser.add_argument("--run-id", default="issue38-local-wsl-paired-signal")
    parser.add_argument("--config-id", default="local-wsl-real-sample-provider-v1")
    return parser


def _looks_like_fixture_provider(import_path: str) -> bool:
    lowered = import_path.lower()
    return any(marker in lowered for marker in FIXTURE_PROVIDER_MARKERS)


def _load_provider(import_path: str, provider_root: str) -> Callable[..., Iterable[SwitchPointSample]]:
    if ":" not in import_path:
        raise ValueError("--sample-provider must use MODULE:CALLABLE")
    module_name, attr_name = import_path.split(":", 1)
    if not module_name or not attr_name:
        raise ValueError("--sample-provider must use MODULE:CALLABLE")
    root = str(Path(provider_root).resolve())
    if root not in sys.path:
        sys.path.insert(0, root)
    module = importlib.import_module(module_name)
    provider = getattr(module, attr_name)
    if not callable(provider):
        raise ValueError("sample provider is not callable")
    return cast(Callable[..., Iterable[SwitchPointSample]], provider)


def _validate_samples(samples: list[Any]) -> None:
    if not samples:
        raise ValueError("sample provider returned no samples")
    invalid = [sample for sample in samples if not isinstance(sample, SwitchPointSample)]
    if invalid:
        raise ValueError("sample provider must return SwitchPointSample objects")


def _validate_summary(summary: dict[str, Any]) -> None:
    verdict = summary.get("verdict")
    if verdict not in VALID_VERDICTS:
        raise ValueError(f"summary verdict must be one of {sorted(VALID_VERDICTS)}")


def _print_review_summary(artifacts: dict[str, Path], summary: dict[str, Any]) -> None:
    print("#38 local WSL paired signal/smoke summary")
    print(f"verdict={summary['verdict']}")
    print(f"valid_pairs={summary['valid_pairs']}")
    print(f"attempted_pairs={summary['attempted_pairs']}")
    print(f"invalid_pairs={summary['invalid_pairs']}")
    print(f"invalid_rate={summary['invalid_rate']:.3f}")
    print(f"replay_status={summary['replay_status']}")
    print(f"runner_invariant_status={summary['runner_invariant_status']}")
    print(f"readout_horizon_steps={summary['readout_horizon_steps']}")
    print(f"csv={artifacts['csv']}")
    print(f"markdown={artifacts['markdown']}")
    print(f"json={artifacts['json']}")
    print("evidence_label=signal_smoke_only")
    print("non_claim=not belief evidence; no ranger-efficacy claim")


if __name__ == "__main__":
    raise SystemExit(main())
