#!/usr/bin/env python3
"""Build sanitized public evidence snapshots from project-authored registries."""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import re
from collections import Counter
from pathlib import Path
from typing import Any

from common import (
    BASELINE_MIN_COUNTS,
    RELEASE_FILES,
    read_json,
    read_jsonl,
    sha256_file,
    write_json,
    write_jsonl,
)

RELEASE_VERSION = "1.1.0"
RELEASE_SCHEMA_VERSION = "1.0"

SOURCE_FILES = {
    "claims": "claim-registry.jsonl",
    "formulas": "formula-registry.jsonl",
    "visuals": "visual-registry.jsonl",
    "rules": "rule-registry.jsonl",
}

OVERLAY_FILES = {
    "claims": "claim-registry.delta.jsonl",
    "formulas": "formula-registry.delta.jsonl",
    "visuals": "visual-registry.delta.jsonl",
    "rules": "rule-registry.delta.jsonl",
}

ID_FIELDS = {
    "claims": "claim_id",
    "formulas": "formula_id",
    "visuals": "visual_id",
    "rules": "rule_id",
}

SOURCES: list[dict[str, Any]] = [
    {
        "source_id": "XZ-E43",
        "kind": "podcast_interview",
        "title": "E43《没有更好的生活》",
        "author_or_speaker": "许哲等",
        "edition": "timestamped episode",
        "publisher": None,
        "isbn": None,
        "locator_convention": "HH:MM:SS time range",
        "local_formats": [".m4a", ".mp3", ".wav", ".md", ".txt"],
        "acquisition_note": "Use a lawfully obtained episode or transcript; verify audio-sensitive wording against the recording.",
    },
    {
        "source_id": "DH-PDF-1997",
        "kind": "book",
        "title": "Dynamic Hedging: Managing Vanilla and Exotic Options",
        "author_or_speaker": "Nassim Nicholas Taleb",
        "edition": "1997",
        "publisher": "John Wiley & Sons",
        "isbn": "978-0-471-15280-4",
        "locator_convention": "physical page and printed page when available",
        "local_formats": [".pdf", ".djvu", ".epub"],
        "acquisition_note": "Use a lawfully obtained edition; page offsets may differ.",
    },
    {
        "source_id": "TALEB-ANTIFRAGILE",
        "kind": "book",
        "title": "Antifragile: Things That Gain from Disorder",
        "author_or_speaker": "Nassim Nicholas Taleb",
        "edition": "edition varies",
        "publisher": None,
        "isbn": None,
        "locator_convention": "chapter and printed-page anchor",
        "local_formats": [".pdf", ".epub"],
        "acquisition_note": "Use a lawfully obtained edition and record edition-specific page mapping locally.",
    },
    {
        "source_id": "TALEB-BLACK-SWAN",
        "kind": "book",
        "title": "The Black Swan",
        "author_or_speaker": "Nassim Nicholas Taleb",
        "edition": "edition varies",
        "publisher": None,
        "isbn": None,
        "locator_convention": "chapter, physical page, and printed page when available",
        "local_formats": [".pdf", ".epub"],
        "acquisition_note": "Use a lawfully obtained edition and record edition-specific page mapping locally.",
    },
    {
        "source_id": "TALEB-FOOLED",
        "kind": "book",
        "title": "Fooled by Randomness",
        "author_or_speaker": "Nassim Nicholas Taleb",
        "edition": "edition varies",
        "publisher": None,
        "isbn": None,
        "locator_convention": "chapter, physical page, and printed page when available",
        "local_formats": [".pdf", ".epub"],
        "acquisition_note": "Use a lawfully obtained edition and record edition-specific page mapping locally.",
    },
    {
        "source_id": "TALEB-SKIN",
        "kind": "book",
        "title": "Skin in the Game",
        "author_or_speaker": "Nassim Nicholas Taleb",
        "edition": "edition varies",
        "publisher": None,
        "isbn": None,
        "locator_convention": "chapter and printed-page anchor",
        "local_formats": [".pdf", ".epub"],
        "acquisition_note": "Use a lawfully obtained edition and record edition-specific page mapping locally.",
    },
    {
        "source_id": "SCOFT-3E-2025",
        "kind": "book",
        "title": "Statistical Consequences of Fat Tails: Real World Preasymptotics, Epistemology, and Applications — Papers and Commentary",
        "author_or_speaker": "Nassim Nicholas Taleb",
        "edition": "Third Edition, 2025",
        "publisher": "STEM Academic Press",
        "isbn": "979-8-218-24803-1",
        "locator_convention": "physical PDF page, chapter, equation, and figure when available",
        "local_formats": [".pdf", ".epub", ".md"],
        "acquisition_note": "Use a lawfully obtained Third Edition. Keep the original file, OCR, page images, hashes, and locator-review artifacts outside the public Skill.",
    },
    {
        "source_id": "CROSS-SOURCE",
        "kind": "project_synthesis",
        "title": "Cross-source option-method derivations",
        "author_or_speaker": "Taleb Options Research contributors",
        "edition": RELEASE_VERSION,
        "publisher": None,
        "isbn": None,
        "locator_convention": "stable formula or rule ID",
        "local_formats": [".md", ".json", ".jsonl"],
        "acquisition_note": "Bundled project-authored synthesis; no third-party source file is required.",
    },
]

PATH_FRAGMENT_RE = re.compile(
    r"(?i)(?:[a-z]:\\[^\s]+|(?:ocr_pipeline|epub_analysis|tmp|research)/[^\s`]+)"
)


def compact(value: Any, limit: int) -> Any:
    if isinstance(value, str):
        text = re.sub(r"\s+", " ", value).strip()
        text = PATH_FRAGMENT_RE.sub("[local material omitted]", text)
        if len(text) <= limit:
            return text
        cut = max(text.rfind(mark, 0, limit) for mark in "。；;.!?")
        if cut < max(40, limit // 2):
            cut = limit - 1
        return text[: cut + 1].rstrip() + "…"
    if isinstance(value, list):
        return [compact(item, limit) for item in value]
    if isinstance(value, dict):
        return {key: compact(item, limit) for key, item in value.items()}
    return value


def public_status(*values: Any) -> tuple[str, str | None]:
    combined = " ".join(str(value) for value in values if value is not None)
    if len(combined) > 1800:
        return (
            "WITHHELD_FROM_PUBLIC_RELEASE",
            "record exceeded the public-summary budget",
        )
    return "PUBLIC_SUMMARY", None


def convert_claim(row: dict[str, Any]) -> dict[str, Any]:
    status, reason = public_status(
        row.get("claim_zh"), row.get("strategy_use"), row.get("limitations")
    )
    result = {
        "claim_id": row["claim_id"],
        "source_id": row["source_id"],
        "locator": compact(row.get("locator"), 180),
        "evidence_level": row.get("evidence_level"),
        "confidence": row.get("confidence"),
        "release_status": status,
        "summary_zh": compact(row.get("claim_zh"), 220)
        if status == "PUBLIC_SUMMARY"
        else None,
        "research_use": compact(row.get("strategy_use"), 180)
        if status == "PUBLIC_SUMMARY"
        else None,
        "limitations": compact(row.get("limitations"), 200)
        if status == "PUBLIC_SUMMARY"
        else None,
        "is_verbatim_quote": False,
    }
    if reason:
        result["withheld_reason"] = reason
    return result


def convert_formula(row: dict[str, Any]) -> dict[str, Any]:
    status, reason = public_status(
        row.get("latex"), row.get("assumptions"), row.get("strategy_effect")
    )
    result = {
        "formula_id": row["formula_id"],
        "source_id": row["source_id"],
        "locator": compact(row.get("locator"), 180),
        "evidence_level": row.get("evidence_level"),
        "source_status": row.get("status"),
        "release_status": status,
        "expression_latex": compact(row.get("latex"), 260)
        if status == "PUBLIC_SUMMARY"
        else None,
        "assumptions": compact(row.get("assumptions"), 200)
        if status == "PUBLIC_SUMMARY"
        else None,
        "strategy_effect": compact(row.get("strategy_effect"), 200)
        if status == "PUBLIC_SUMMARY"
        else None,
    }
    if reason:
        result["withheld_reason"] = reason
    return result


def convert_visual(row: dict[str, Any]) -> dict[str, Any]:
    status, reason = public_status(row.get("supports"), row.get("does_not_support"))
    result = {
        "visual_id": row["visual_id"],
        "source_id": row["source_id"],
        "locator": compact(row.get("locator"), 180),
        "review_status": row.get("review_status"),
        "release_status": status,
        "supports": compact(row.get("supports"), 220)
        if status == "PUBLIC_SUMMARY"
        else None,
        "does_not_support": compact(row.get("does_not_support"), 220)
        if status == "PUBLIC_SUMMARY"
        else None,
        "bundled": False,
    }
    if reason:
        result["withheld_reason"] = reason
    return result


def convert_rule(row: dict[str, Any]) -> dict[str, Any]:
    status, reason = public_status(
        row.get("trigger"), row.get("action"), row.get("risk_guard")
    )
    result = {
        "rule_id": row["rule_id"],
        "family": row.get("family"),
        "evidence_level": row.get("evidence_level", "A"),
        "source_status": row.get("status"),
        "release_status": status,
        "evidence_refs": row.get("evidence_refs", []),
        "formula_refs": row.get("formula_refs", []),
        "visual_refs": row.get("visual_refs", []),
        "trigger": compact(row.get("trigger"), 180)
        if status == "PUBLIC_SUMMARY"
        else None,
        "action": compact(row.get("action"), 240)
        if status == "PUBLIC_SUMMARY"
        else None,
        "risk_guard": compact(row.get("risk_guard"), 220)
        if status == "PUBLIC_SUMMARY"
        else None,
        "unknowns": compact(row.get("unknowns", []), 160),
        "test_refs": compact(row.get("test_refs", []), 160),
    }
    if reason:
        result["withheld_reason"] = reason
    return result


def source_counts(
    rows_by_kind: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for kind, rows in rows_by_kind.items():
        counts = Counter(str(row.get("source_id", "PROJECT_RULE")) for row in rows)
        for source_id, count in counts.items():
            result.setdefault(source_id, {})[kind] = count
    return result


def write_source_documents(
    output_dir: Path, rows_by_kind: dict[str, list[dict[str, Any]]], release_date: str
) -> None:
    counts = source_counts(rows_by_kind)
    inventory = [
        "# Public source inventory",
        "",
        f"Release: {RELEASE_VERSION} ({release_date})",
        "",
        "This inventory contains bibliographic and locator metadata only. Original books, audio, transcripts, OCR, page images, and local paths are not bundled.",
        "",
        "| Source ID | Title | Author/speaker | Edition | Locator |",
        "|---|---|---|---|---|",
    ]
    for source in SOURCES:
        inventory.append(
            f"| `{source['source_id']}` | {source['title']} | {source['author_or_speaker']} | "
            f"{source['edition']} | {source['locator_convention']} |"
        )
    (output_dir / "source-inventory.release.md").write_text(
        "\n".join(inventory) + "\n", encoding="utf-8", newline="\n"
    )

    coverage = [
        "# Public source coverage",
        "",
        f"Release: {RELEASE_VERSION} ({release_date})",
        "",
        "Counts describe project-authored release records, not copied pages. A zero count does not mean a source lacks value; it means that registry type has no released record for the source.",
        "",
        "| Source ID | Claims | Formulas | Visual metadata | Rules |",
        "|---|---:|---:|---:|---:|",
    ]
    for source in SOURCES:
        item = counts.get(source["source_id"], {})
        coverage.append(
            f"| `{source['source_id']}` | {item.get('claims', 0)} | {item.get('formulas', 0)} | "
            f"{item.get('visuals', 0)} | {item.get('rules', 0)} |"
        )
    coverage.extend(
        [
            "",
            "Coverage depth and evidence levels remain record-specific. Use the registries and locators; do not infer that every chapter or page has been reproduced or directly rechecked in the current session.",
        ]
    )
    (output_dir / "source-coverage.release.md").write_text(
        "\n".join(coverage) + "\n", encoding="utf-8", newline="\n"
    )

    source_map = [
        "# Source map",
        "",
        "Use stable IDs and locators to navigate evidence. These entries are not download links.",
        "",
        "| Source ID | Primary research role | Locator convention |",
        "|---|---|---|",
        "| `XZ-E43` | Xu Zhe interview claims, structure hints, roll ambiguity | timestamp range |",
        "| `DH-PDF-1997` | option structure, Greeks, path, execution, compound and exotic contracts | physical/printed page |",
        "| `TALEB-ANTIFRAGILE` | convexity, optionality, barbell, model fragility | chapter/page anchor |",
        "| `TALEB-BLACK-SWAN` | tail uncertainty and model-extrapolation limits | chapter/physical/printed page |",
        "| `TALEB-FOOLED` | selection, luck, path, sampling and multiplicity | chapter/physical/printed page |",
        "| `TALEB-SKIN` | ruin, time probability, incentives and account survival | chapter/page anchor |",
        "| `SCOFT-3E-2025` | preasymptotics, fat-tail estimation, option-price measures, hedge error, dependence and tail constraints | physical PDF page/chapter/equation/figure |",
        "| `CROSS-SOURCE` | project-authored formulas and governance synthesis | stable record ID |",
        "",
        "Search examples:",
        "",
        "```text",
        'rg \'"claim_id":"XZ-D-03"\' references/claim-registry.release.jsonl',
        'rg \'"formula_id":"DH-A-WING-PAYOFF-01"\' references/formula-registry.release.jsonl',
        'rg \'"rule_id":"RULE-SCOFT-PREASYMPTOTIC-01"\' references/rule-registry.release.jsonl',
        'rg \'"family":"F3"\' references/rule-registry.release.jsonl',
        "```",
    ]
    (output_dir / "source-map.md").write_text(
        "\n".join(source_map) + "\n", encoding="utf-8", newline="\n"
    )


def write_strategy_fixtures(strategy_artifact: Path, fixtures_dir: Path) -> None:
    document = read_json(strategy_artifact)
    valid = copy.deepcopy(document)
    valid["specs"] = [copy.deepcopy(document["specs"][0])]
    write_json(fixtures_dir / "valid-single.json", valid)

    missing = copy.deepcopy(valid)
    missing.pop("artifact_status", None)
    write_json(fixtures_dir / "invalid-missing-fields.json", missing)

    authority = copy.deepcopy(valid)
    authority["execution_authority"] = True
    write_json(fixtures_dir / "invalid-production-authority.json", authority)

    parameter = copy.deepcopy(valid)
    parameter["specs"][0]["parameter_registry"][0]["status"] = "GUESSED_DEFAULT"
    write_json(fixtures_dir / "invalid-parameter-status.json", parameter)


def validate_raw_records(raw: dict[str, list[dict[str, Any]]]) -> None:
    source_ids = {source["source_id"] for source in SOURCES}
    ids = {kind: {row[ID_FIELDS[kind]] for row in rows} for kind, rows in raw.items()}
    errors: list[str] = []

    for kind in ["claims", "formulas", "visuals"]:
        for index, row in enumerate(raw[kind], 1):
            if row.get("source_id") not in source_ids:
                errors.append(
                    f"{kind}:{index}: unknown source_id {row.get('source_id')}"
                )

    for index, row in enumerate(raw["rules"], 1):
        for field, target_kind in [
            ("evidence_refs", "claims"),
            ("formula_refs", "formulas"),
            ("visual_refs", "visuals"),
        ]:
            for ref in row.get(field, []):
                if ref not in ids[target_kind]:
                    errors.append(f"rules:{index}.{field}: dangling reference {ref}")

    if errors:
        raise SystemExit("\n".join(errors))


def build(args: argparse.Namespace) -> None:
    source_dir = args.source_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    raw = {
        kind: read_jsonl(source_dir / filename)
        for kind, filename in SOURCE_FILES.items()
    }
    for kind, minimum in BASELINE_MIN_COUNTS.items():
        if len(raw[kind]) < minimum:
            raise SystemExit(
                f"{kind}: expected at least {minimum} baseline rows, found {len(raw[kind])}"
            )

    for overlay_dir in args.overlay_dir:
        overlay_dir = overlay_dir.resolve()
        for kind, filename in OVERLAY_FILES.items():
            path = overlay_dir / filename
            if not path.is_file():
                raise SystemExit(f"{kind}: missing overlay file {path}")
            raw[kind].extend(read_jsonl(path))

    for kind, rows in raw.items():
        id_field = ID_FIELDS[kind]
        seen: set[str] = set()
        for index, row in enumerate(rows, 1):
            record_id = row.get(id_field)
            if not isinstance(record_id, str) or not record_id:
                raise SystemExit(f"{kind}:{index}: missing or invalid {id_field}")
            if record_id in seen:
                raise SystemExit(f"{kind}:{index}: duplicate ID {record_id}")
            seen.add(record_id)
        rows.sort(key=lambda row: row[id_field])
    validate_raw_records(raw)

    released = {
        "claims": [convert_claim(row) for row in raw["claims"]],
        "formulas": [convert_formula(row) for row in raw["formulas"]],
        "visuals": [convert_visual(row) for row in raw["visuals"]],
        "rules": [convert_rule(row) for row in raw["rules"]],
    }

    for kind, filename in RELEASE_FILES.items():
        write_jsonl(output_dir / filename, released[kind])

    schema = copy.deepcopy(read_json(source_dir / "strategy-spec.schema.json"))
    schema["$id"] = "urn:taleb-options-research:strategy-spec:1.1"
    schema["title"] = "Taleb options research StrategySpec"
    schema["properties"]["specs"]["minItems"] = 1
    schema["$defs"]["strategySpec"]["properties"]["fat_tail_robustness"] = {
        "$ref": "#/$defs/fatTailRobustness"
    }
    schema["$defs"]["fatTailRobustness"] = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "preasymptotic_tests",
            "moment_requirements",
            "extreme_scenarios",
            "parameter_uncertainty",
            "probability_measure_labels",
            "joint_tail_tests",
            "hedge_error_tests",
            "selection_controls",
            "tail_constraint",
        ],
        "properties": {
            field: {
                "type": "array",
                "minItems": 1,
                "uniqueItems": True,
                "items": {"type": "string", "minLength": 1},
            }
            for field in [
                "preasymptotic_tests",
                "moment_requirements",
                "extreme_scenarios",
                "parameter_uncertainty",
                "probability_measure_labels",
                "joint_tail_tests",
                "hedge_error_tests",
                "selection_controls",
            ]
        }
        | {
            "tail_constraint": {
                "type": "string",
                "minLength": 1,
            }
        },
    }
    write_json(output_dir / "strategy-spec.schema.json", schema)

    write_source_documents(output_dir, released, args.release_date)

    artifacts = []
    for kind, filename in RELEASE_FILES.items():
        path = output_dir / filename
        artifacts.append(
            {
                "kind": kind,
                "path": filename,
                "records": len(released[kind]),
                "sha256": sha256_file(path),
            }
        )
    for filename in [
        "source-inventory.release.md",
        "source-coverage.release.md",
        "source-map.md",
        "strategy-spec.schema.json",
    ]:
        path = output_dir / filename
        artifacts.append(
            {
                "kind": "document",
                "path": filename,
                "records": None,
                "sha256": sha256_file(path),
            }
        )

    manifest = {
        "schema_version": RELEASE_SCHEMA_VERSION,
        "release_version": RELEASE_VERSION,
        "generated_at": args.release_date,
        "license": {
            "code_and_schema": "Apache-2.0",
            "original_documentation_and_release_summaries": "CC-BY-4.0",
            "third_party_sources": "EXCLUDED_NOT_BUNDLED_NOT_RELICENSED",
        },
        "sources": SOURCES,
        "release_artifacts": artifacts,
        "raw_source_hash_policy": "Local source hashes are user-specific BYOS metadata and are not canonical release hashes.",
    }
    write_json(output_dir / "source-manifest.json", manifest)
    if args.strategy_artifact:
        write_strategy_fixtures(
            args.strategy_artifact.resolve(),
            Path(__file__).resolve().parent / "fixtures" / "strategy",
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument(
        "--overlay-dir",
        type=Path,
        action="append",
        default=[],
        help="Directory containing the four *.delta.jsonl overlay registries; repeatable.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "references",
    )
    parser.add_argument(
        "--release-date",
        default=dt.datetime.now(dt.timezone.utc).date().isoformat(),
    )
    parser.add_argument("--strategy-artifact", type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    build(parse_args())
