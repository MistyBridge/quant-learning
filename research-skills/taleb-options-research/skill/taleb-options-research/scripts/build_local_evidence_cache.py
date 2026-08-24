#!/usr/bin/env python3
"""Build an offline locator-review cache outside the public Skill."""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from common import (
    RELEASE_FILES,
    ValidationError,
    is_within,
    read_json,
    read_jsonl,
    write_json,
    write_jsonl,
)
from verify_source_manifest import verify_index


def load_mapping(path: Path | None, known_ids: set[str]) -> list[dict]:
    if path is None:
        return []
    rows = read_jsonl(path)
    for index, row in enumerate(rows, 1):
        required = {"source_id", "locator", "local_locator", "review_status"}
        missing = required - row.keys()
        if missing:
            raise ValidationError(
                f"{path}:{index}: missing mapping fields {sorted(missing)}"
            )
        if row["source_id"] not in known_ids:
            raise ValidationError(
                f"{path}:{index}: mapping references unknown source {row['source_id']}"
            )
    return rows


def build_cache(
    index_path: Path,
    manifest_path: Path,
    references_dir: Path,
    evidence_root: Path,
    mapping_path: Path | None,
) -> dict:
    skill_root = Path(__file__).resolve().parents[1]
    evidence_root = evidence_root.expanduser().resolve()
    if is_within(evidence_root, skill_root) or is_within(skill_root, evidence_root):
        raise ValidationError("evidence root must be separate from the Skill directory")
    if evidence_root == Path(evidence_root.anchor):
        raise ValidationError("refusing to use a filesystem root as evidence root")

    report = verify_index(index_path, manifest_path)
    if report["results"] and not report["all_usable"]:
        raise ValidationError("source verification failed; cache was not created")

    index = read_json(index_path)
    known_ids = {item["source_id"] for item in index.get("entries", [])}
    mappings = load_mapping(mapping_path, known_ids)

    queue: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for kind, filename in RELEASE_FILES.items():
        for row in read_jsonl(references_dir / filename):
            source_id = row.get("source_id")
            locator = row.get("locator")
            if (
                not isinstance(source_id, str)
                or source_id not in known_ids
                or not isinstance(locator, str)
                or not locator
            ):
                continue
            key = (source_id, locator)
            if key in seen:
                continue
            seen.add(key)
            queue.append(
                {
                    "source_id": source_id,
                    "locator": locator,
                    "review_status": "PENDING_LOCAL_PAGE_MATCH",
                    "evidence_kind": kind,
                }
            )

    evidence_root.mkdir(parents=True, exist_ok=True)
    cache_manifest = {
        "schema_version": "1.0",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "mode": "PUBLIC_CORE_ONLY" if not known_ids else "BYOS_LOCAL_CACHE",
        "source_verification": report,
        "local_index": index,
        "locator_queue_records": len(queue),
        "mapping_records": len(mappings),
        "content_uploaded": False,
        "network_used": False,
    }
    write_json(evidence_root / "cache-manifest.json", cache_manifest)
    write_jsonl(evidence_root / "locator-review-queue.jsonl", queue)
    write_jsonl(evidence_root / "local-locator-mapping.jsonl", mappings)
    return cache_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("index", type=Path)
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=Path.home() / ".codex" / "evidence" / "taleb-options-research",
    )
    parser.add_argument("--mapping", type=Path)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "references"
        / "source-manifest.json",
    )
    parser.add_argument(
        "--references-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "references",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        result = build_cache(
            args.index,
            args.manifest,
            args.references_dir,
            args.evidence_root,
            args.mapping,
        )
    except (ValidationError, OSError, ValueError) as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
    print(
        f"PASS: mode={result['mode']} locator_queue_records={result['locator_queue_records']}"
    )
