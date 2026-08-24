#!/usr/bin/env python3
"""Validate StrategySpec JSON with schema and cross-record research invariants."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

try:
    import jsonschema
except ImportError as exc:  # pragma: no cover - environment-dependent path
    raise SystemExit(
        "jsonschema is required. Run with: uv run --with jsonschema python "
        "scripts/validate_strategy_spec.py <artifact.json> --mode single"
    ) from exc

from common import ValidationError, read_json

PARAMETER_STATUSES = {
    "CONTRACT",
    "LITERATURE",
    "CALIBRATE",
    "USER_POLICY",
    "STRESS",
    "MISSING_FROM_SOURCE",
    "UNKNOWN",
}

DECISION_STATES = {
    "RESEARCH",
    "SPEC_VALID",
    "DATA_READY",
    "SIM_PASS",
    "HOLDOUT_PASS",
    "PAPER_WATCH",
    "REJECT",
    "NO_TRADE",
}

PORTFOLIO_COUNTS = {"candidate": 4, "baseline": 5, "no_trade": 1}


def validate_semantics(document: dict[str, Any], mode: str) -> list[str]:
    errors: list[str] = []
    specs = document.get("specs", [])
    if mode == "single" and len(specs) != 1:
        errors.append(f"single mode requires exactly 1 spec, found {len(specs)}")
    if mode == "portfolio":
        counts = Counter(spec.get("class") for spec in specs)
        for class_name, expected in PORTFOLIO_COUNTS.items():
            if counts.get(class_name, 0) != expected:
                errors.append(
                    f"portfolio mode requires {expected} {class_name} specs, "
                    f"found {counts.get(class_name, 0)}"
                )
        if len(specs) != sum(PORTFOLIO_COUNTS.values()):
            errors.append(
                f"portfolio mode requires exactly 10 specs, found {len(specs)}"
            )

    if document.get("execution_authority") is not False:
        errors.append("execution_authority must be false")
    if set(document.get("parameter_status_enum", [])) != PARAMETER_STATUSES:
        errors.append("parameter_status_enum must match the canonical set")
    if set(document.get("decision_state_enum", [])) != DECISION_STATES:
        errors.append("decision_state_enum must match the canonical set")

    profiles = document.get("passport_profiles", {})
    spec_ids: set[str] = set()
    for index, spec in enumerate(specs):
        label = spec.get("spec_id") or f"spec[{index}]"
        if label in spec_ids:
            errors.append(f"duplicate spec_id {label}")
        spec_ids.add(label)

        for profile_id in spec.get("required_profile_ids", []):
            if profile_id not in profiles:
                errors.append(f"{label}: unknown required_profile_id {profile_id}")

        for parameter in spec.get("parameter_registry", []):
            status = parameter.get("status")
            if status not in PARAMETER_STATUSES:
                errors.append(f"{label}: invalid parameter status {status}")
            if (
                status == "MISSING_FROM_SOURCE"
                and parameter.get("source_value") is not None
            ):
                errors.append(
                    f"{label}:{parameter.get('name')}: MISSING_FROM_SOURCE must use null source_value"
                )

        if label == "F3_DYNAMIC_HARVEST_REBUILD":
            legs = spec.get("canonical_legs", [])
            if not any(leg.get("side") == "branch_unresolved" for leg in legs):
                errors.append(f"{label}: must preserve an unresolved action branch")
            direction = next(
                (
                    item
                    for item in spec.get("parameter_registry", [])
                    if item.get("name") == "replacement_put_direction"
                ),
                None,
            )
            if not direction or direction.get("status") != "UNKNOWN":
                errors.append(f"{label}: replacement_put_direction must remain UNKNOWN")

        if label == "F5_NO_TRADE" and spec.get("class") != "no_trade":
            errors.append("F5_NO_TRADE must have class no_trade")

    if mode == "portfolio":
        for spec in specs:
            label = spec.get("spec_id")
            for benchmark_id in spec.get("benchmark_ids", []):
                if benchmark_id not in spec_ids:
                    errors.append(f"{label}: dangling benchmark_id {benchmark_id}")

    return errors


def validate_document(
    document: dict[str, Any], schema: dict[str, Any], mode: str
) -> None:
    validator = jsonschema.Draft202012Validator(schema)
    schema_errors = sorted(
        validator.iter_errors(document), key=lambda item: list(item.path)
    )
    errors = [
        f"schema at {'/'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
        for error in schema_errors
    ]
    errors.extend(validate_semantics(document, mode))
    if errors:
        raise ValidationError("\n".join(errors))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--mode", choices=["single", "portfolio"], required=True)
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "references"
        / "strategy-spec.schema.json",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        document = read_json(args.artifact)
        schema = read_json(args.schema)
        validate_document(document, schema, args.mode)
    except (ValidationError, json.JSONDecodeError, OSError, ValueError) as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
    print(f"PASS: {args.artifact} ({args.mode})")
