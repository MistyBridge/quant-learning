#!/usr/bin/env python3
"""Run offline regression tests for the public Skill."""

from __future__ import annotations

import tempfile
from pathlib import Path

from build_local_evidence_cache import build_cache
from common import ValidationError, read_json, scan_text
from index_local_sources import build_index
from validate_release_evidence import validate as validate_release
from validate_strategy_spec import validate_document
from verify_source_manifest import verify_index


def expect_failure(callable_obj, label: str) -> None:
    try:
        callable_obj()
    except (ValidationError, ValueError):
        return
    raise AssertionError(f"{label}: expected failure")


def main() -> None:
    skill_root = Path(__file__).resolve().parents[1]
    references = skill_root / "references"
    fixtures = Path(__file__).resolve().parent / "fixtures"

    release_summary = validate_release(references)
    assert release_summary["release_version"] == "1.1.0"
    assert release_summary["counts"] == {
        "claims": 422,
        "formulas": 233,
        "visuals": 245,
        "rules": 183,
    }

    schema = read_json(references / "strategy-spec.schema.json")
    valid = read_json(fixtures / "strategy" / "valid-single.json")
    validate_document(valid, schema, "single")
    fat_tail_valid = read_json(fixtures / "strategy" / "valid-single.json")
    fat_tail_valid["specs"][0]["fat_tail_robustness"] = {
        "preasymptotic_tests": ["nested sample and seed stability"],
        "moment_requirements": ["declare every estimator's required moment"],
        "extreme_scenarios": ["one-big-jump and beyond-historical-maximum stress"],
        "parameter_uncertainty": ["sweep tail and volatility parameters"],
        "probability_measure_labels": ["label P, Q, subjective and stress separately"],
        "joint_tail_tests": ["co-jump and liquidity-withdrawal stress"],
        "hedge_error_tests": ["discrete hedge with gap and no-rebalance branches"],
        "selection_controls": ["trial ledger, holdout and walk-forward"],
        "tail_constraint": "user-supplied catastrophic-loss envelope",
    }
    validate_document(fat_tail_valid, schema, "single")
    for filename in [
        "invalid-missing-fields.json",
        "invalid-production-authority.json",
        "invalid-parameter-status.json",
    ]:
        invalid = read_json(fixtures / "strategy" / filename)
        expect_failure(
            lambda invalid=invalid: validate_document(invalid, schema, "single"),
            filename,
        )

    assert scan_text("C:" + r"\Users\example\private\source.txt")
    assert scan_text("github_pat_" + "x" * 40)

    manifest_path = references / "source-manifest.json"
    with tempfile.TemporaryDirectory(prefix="taleb-options-selftest-") as temp_name:
        temp = Path(temp_name)
        source = temp / "project-synthesis.md"
        source.write_bytes((references / "core-method.md").read_bytes())
        index_path = temp / "local-index.json"
        result = build_index(
            [f"CROSS-SOURCE={source}"],
            manifest_path,
            index_path,
        )
        assert len(result["entries"]) == 1
        report = verify_index(index_path, manifest_path)
        assert report["all_usable"] is True

        cache_root = temp / "evidence-cache"
        cache = build_cache(
            index_path,
            manifest_path,
            references,
            cache_root,
            None,
        )
        assert cache["mode"] == "BYOS_LOCAL_CACHE"
        assert (cache_root / "cache-manifest.json").is_file()

        source.write_text("changed", encoding="utf-8")
        mismatch = verify_index(index_path, manifest_path)
        assert mismatch["all_usable"] is False

        empty_index = temp / "empty-index.json"
        empty = build_index([], manifest_path, empty_index)
        assert empty["mode"] == "PUBLIC_CORE_ONLY"
        degraded_root = temp / "degraded-cache"
        degraded = build_cache(
            empty_index,
            manifest_path,
            references,
            degraded_root,
            None,
        )
        assert degraded["mode"] == "PUBLIC_CORE_ONLY"

    print(
        "PASS: release, StrategySpec, leakage, BYOS, mismatch, and degraded-mode tests"
    )


if __name__ == "__main__":
    main()
