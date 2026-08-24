#!/usr/bin/env python3
"""Validate public release registries, manifest hashes, and disclosure boundaries."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import (
    RELEASE_FILES,
    ValidationError,
    read_json,
    read_jsonl,
    require_keys,
    scan_text,
    sha256_file,
)

REQUIRED = {
    "claims": [
        "claim_id",
        "source_id",
        "locator",
        "evidence_level",
        "release_status",
        "summary_zh",
        "is_verbatim_quote",
    ],
    "formulas": [
        "formula_id",
        "source_id",
        "locator",
        "evidence_level",
        "source_status",
        "release_status",
        "expression_latex",
        "assumptions",
    ],
    "visuals": [
        "visual_id",
        "source_id",
        "locator",
        "review_status",
        "release_status",
        "supports",
        "does_not_support",
        "bundled",
    ],
    "rules": [
        "rule_id",
        "family",
        "evidence_level",
        "source_status",
        "release_status",
        "evidence_refs",
        "formula_refs",
        "visual_refs",
        "trigger",
        "action",
        "risk_guard",
        "unknowns",
        "test_refs",
    ],
}

ID_FIELDS = {
    "claims": "claim_id",
    "formulas": "formula_id",
    "visuals": "visual_id",
    "rules": "rule_id",
}

TEXT_LIMITS = {
    "summary_zh": 230,
    "research_use": 190,
    "limitations": 210,
    "expression_latex": 270,
    "assumptions": 210,
    "strategy_effect": 210,
    "supports": 230,
    "does_not_support": 230,
    "trigger": 190,
    "action": 250,
    "risk_guard": 230,
}


def walk_strings(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    if isinstance(value, str):
        result.append((prefix, value))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            result.extend(walk_strings(item, f"{prefix}[{index}]"))
    elif isinstance(value, dict):
        for key, item in value.items():
            result.extend(walk_strings(item, f"{prefix}.{key}" if prefix else key))
    return result


def validate(references_dir: Path) -> dict[str, Any]:
    references_dir = references_dir.resolve()
    manifest = read_json(references_dir / "source-manifest.json")
    errors: list[str] = []
    rows_by_kind: dict[str, list[dict[str, Any]]] = {}
    ids: dict[str, set[str]] = {}
    source_ids = {source["source_id"] for source in manifest.get("sources", [])}
    artifacts = {item["path"]: item for item in manifest.get("release_artifacts", [])}

    for kind, filename in RELEASE_FILES.items():
        path = references_dir / filename
        rows = read_jsonl(path)
        rows_by_kind[kind] = rows
        artifact = artifacts.get(filename)
        expected = artifact.get("records") if artifact else None
        if expected is not None and len(rows) != expected:
            errors.append(
                f"{filename}: manifest expects {expected} rows, found {len(rows)}"
            )

        id_field = ID_FIELDS[kind]
        id_values: set[str] = set()
        for index, row in enumerate(rows, 1):
            label = f"{filename}:{index}"
            try:
                require_keys(row, REQUIRED[kind], label)
            except ValidationError as exc:
                errors.append(str(exc))
                continue

            record_id = row.get(id_field)
            if not isinstance(record_id, str) or not record_id:
                errors.append(f"{label}: invalid {id_field}")
            elif record_id in id_values:
                errors.append(f"{label}: duplicate ID {record_id}")
            else:
                id_values.add(record_id)

            if row.get("release_status") not in {
                "PUBLIC_SUMMARY",
                "WITHHELD_FROM_PUBLIC_RELEASE",
            }:
                errors.append(f"{label}: invalid release_status")
            if row.get(
                "release_status"
            ) == "WITHHELD_FROM_PUBLIC_RELEASE" and not row.get("withheld_reason"):
                errors.append(f"{label}: withheld record lacks withheld_reason")

            if kind != "rules" and row.get("source_id") not in source_ids:
                errors.append(f"{label}: unknown source_id {row.get('source_id')}")
            if kind == "claims" and row.get("is_verbatim_quote") is not False:
                errors.append(f"{label}: release claim must not be a verbatim quote")
            if kind == "rules" and row.get("evidence_level") != "A":
                errors.append(f"{label}: project-derived rule evidence_level must be A")
            if kind == "visuals":
                if "image_path" in row:
                    errors.append(f"{label}: image_path is forbidden")
                if row.get("bundled") is not False:
                    errors.append(f"{label}: bundled must be false")

            for field, text in walk_strings(row):
                for finding in scan_text(text):
                    errors.append(f"{label}.{field}: {finding}")
                leaf = field.split(".")[-1].split("[")[0]
                if leaf in TEXT_LIMITS and len(text) > TEXT_LIMITS[leaf]:
                    errors.append(
                        f"{label}.{field}: length {len(text)} exceeds {TEXT_LIMITS[leaf]}"
                    )
        ids[kind] = id_values

    for index, row in enumerate(rows_by_kind.get("rules", []), 1):
        for field, kind in [
            ("evidence_refs", "claims"),
            ("formula_refs", "formulas"),
            ("visual_refs", "visuals"),
        ]:
            for ref in row.get(field, []):
                if ref not in ids.get(kind, set()):
                    errors.append(
                        f"{RELEASE_FILES['rules']}:{index}.{field}: dangling reference {ref}"
                    )

    for filename in [
        *RELEASE_FILES.values(),
        "source-inventory.release.md",
        "source-coverage.release.md",
        "source-map.md",
        "strategy-spec.schema.json",
    ]:
        path = references_dir / filename
        item = artifacts.get(filename)
        if not item:
            errors.append(f"source-manifest.json: missing artifact {filename}")
            continue
        actual_hash = sha256_file(path)
        if item.get("sha256") != actual_hash:
            errors.append(f"source-manifest.json: hash mismatch for {filename}")
        if filename in RELEASE_FILES.values():
            kind = next(
                key for key, value in RELEASE_FILES.items() if value == filename
            )
            if item.get("records") != len(rows_by_kind[kind]):
                errors.append(
                    f"source-manifest.json: record count mismatch for {filename}"
                )

    if errors:
        raise ValidationError("\n".join(errors))

    return {
        "release_version": manifest.get("release_version"),
        "counts": {kind: len(rows) for kind, rows in rows_by_kind.items()},
        "withheld": {
            kind: sum(
                row.get("release_status") == "WITHHELD_FROM_PUBLIC_RELEASE"
                for row in rows
            )
            for kind, rows in rows_by_kind.items()
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--references-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "references",
    )
    return parser.parse_args()


if __name__ == "__main__":
    try:
        summary = validate(parse_args().references_dir)
    except (ValidationError, OSError, ValueError) as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
    print(f"PASS: {summary}")
