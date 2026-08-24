#!/usr/bin/env python3
"""Create an offline, user-specific index for explicitly supplied source files."""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from common import ValidationError, is_within, read_json, sha256_file, write_json


def parse_source_spec(spec: str) -> tuple[str, Path]:
    if "=" not in spec:
        raise ValidationError(f"expected SOURCE_ID=PATH, got {spec!r}")
    source_id, raw_path = spec.split("=", 1)
    source_id = source_id.strip()
    if not source_id:
        raise ValidationError(f"empty source ID in {spec!r}")
    path = Path(raw_path.strip()).expanduser().resolve()
    if not path.is_file():
        raise ValidationError(f"{source_id}: file does not exist: {path}")
    return source_id, path


def build_index(specs: list[str], manifest_path: Path, output: Path) -> dict:
    skill_root = Path(__file__).resolve().parents[1]
    output = output.expanduser().resolve()
    if is_within(output, skill_root):
        raise ValidationError(
            "local source indexes must be stored outside the Skill directory"
        )

    manifest = read_json(manifest_path)
    known_sources = {
        source["source_id"]: source for source in manifest.get("sources", [])
    }
    entries = []
    seen: set[str] = set()
    for spec in specs:
        source_id, path = parse_source_spec(spec)
        if source_id in seen:
            raise ValidationError(f"duplicate source ID: {source_id}")
        seen.add(source_id)
        known = known_sources.get(source_id)
        entries.append(
            {
                "source_id": source_id,
                "path": str(path),
                "filename": path.name,
                "format": path.suffix.lower(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "manifest_known": known is not None,
                "title": known.get("title") if known else None,
                "edition_match": "UNVERIFIED",
                "content_uploaded": False,
            }
        )

    result = {
        "schema_version": "1.0",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "mode": "PUBLIC_CORE_ONLY" if not entries else "BYOS_LOCAL_INDEX",
        "user_attestation": "Paths were explicitly supplied; the tool does not determine whether acquisition was lawful.",
        "entries": entries,
    }
    write_json(output, result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("sources", nargs="*", help="One or more SOURCE_ID=PATH values")
    parser.add_argument("--output", type=Path, required=True)
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
        result = build_index(args.sources, args.manifest, args.output)
    except (ValidationError, OSError, ValueError) as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
    print(f"PASS: indexed {len(result['entries'])} explicit local source(s)")
