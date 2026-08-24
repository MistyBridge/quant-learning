#!/usr/bin/env python3
"""Verify a user-specific BYOS index against public source metadata."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import ValidationError, read_json, sha256_file, write_json


def verify_index(index_path: Path, manifest_path: Path) -> dict[str, Any]:
    index = read_json(index_path)
    manifest = read_json(manifest_path)
    known_sources = {
        source["source_id"]: source for source in manifest.get("sources", [])
    }
    results = []
    for entry in index.get("entries", []):
        source_id = entry.get("source_id")
        path = Path(str(entry.get("path", ""))).expanduser()
        source = known_sources.get(source_id)
        reasons: list[str] = []
        status = "AVAILABLE_UNVERIFIED_EDITION"

        if source is None:
            status = "UNKNOWN_SOURCE"
            reasons.append("source_id is not present in the public manifest")
        if not path.is_file():
            status = "MISMATCH"
            reasons.append("indexed file is missing")
        else:
            actual_hash = sha256_file(path)
            if actual_hash != entry.get("sha256"):
                status = "MISMATCH"
                reasons.append("file SHA-256 changed after indexing")
            if entry.get("size_bytes") != path.stat().st_size:
                status = "MISMATCH"
                reasons.append("file size changed after indexing")
            if source and path.suffix.lower() not in source.get("local_formats", []):
                status = "MISMATCH"
                reasons.append(
                    f"format {path.suffix.lower()} is not registered for {source_id}"
                )

        results.append(
            {
                "source_id": source_id,
                "status": status,
                "reasons": reasons,
                "sha256": entry.get("sha256"),
                "edition_match": "UNVERIFIED",
                "direct_page_verification": False,
            }
        )

    summary = {
        "schema_version": "1.0",
        "mode": "PUBLIC_CORE_ONLY" if not results else "BYOS_VERIFICATION",
        "all_usable": all(
            item["status"] == "AVAILABLE_UNVERIFIED_EDITION" for item in results
        ),
        "results": results,
        "warning": "A usable local file is not an edition/page match until locator mapping is reviewed.",
    }
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("index", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "references"
        / "source-manifest.json",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        report = verify_index(args.index, args.manifest)
        if args.output:
            write_json(args.output.expanduser().resolve(), report)
    except (ValidationError, OSError, ValueError) as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
    print(f"PASS: {report}")
    if report["results"] and not report["all_usable"]:
        raise SystemExit(1)
