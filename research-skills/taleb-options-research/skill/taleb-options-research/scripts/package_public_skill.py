#!/usr/bin/env python3
"""Build and re-audit an allowlisted public ZIP of the Skill."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from common import ValidationError, scan_tree, sha256_file, write_json
from validate_release_evidence import validate as validate_release

ROOT_FILES = {"SKILL.md", "LICENSE", "LICENSE-DOCS", "NOTICE"}
AGENT_FILES = {"agents/openai.yaml"}
REFERENCE_FILES = {
    "references/core-method.md",
    "references/strategy-families.md",
    "references/evidence-and-parameter-governance.md",
    "references/validation-and-output-contract.md",
    "references/licensing-and-sources.md",
    "references/fat-tail-statistics-and-options.md",
    "references/source-map.md",
    "references/source-manifest.json",
    "references/source-inventory.release.md",
    "references/source-coverage.release.md",
    "references/claim-registry.release.jsonl",
    "references/formula-registry.release.jsonl",
    "references/visual-registry.release.jsonl",
    "references/rule-registry.release.jsonl",
    "references/strategy-spec.schema.json",
}
SCRIPT_FILES = {
    "scripts/common.py",
    "scripts/build_release_evidence.py",
    "scripts/validate_release_evidence.py",
    "scripts/validate_strategy_spec.py",
    "scripts/index_local_sources.py",
    "scripts/verify_source_manifest.py",
    "scripts/build_local_evidence_cache.py",
    "scripts/package_public_skill.py",
    "scripts/run_self_tests.py",
}
FIXTURE_FILES = {
    "scripts/fixtures/strategy/valid-single.json",
    "scripts/fixtures/strategy/invalid-missing-fields.json",
    "scripts/fixtures/strategy/invalid-production-authority.json",
    "scripts/fixtures/strategy/invalid-parameter-status.json",
    "scripts/fixtures/sources/valid-source-manifest.json",
    "scripts/fixtures/sources/local-source-index.sample.json",
    "scripts/fixtures/sources/mismatched-source-index.sample.json",
}
ALLOWLIST = ROOT_FILES | AGENT_FILES | REFERENCE_FILES | SCRIPT_FILES | FIXTURE_FILES
IGNORED_PARTS = {"__pycache__", ".pytest_cache"}


def collect_files(skill_root: Path) -> dict[str, Path]:
    skill_root = skill_root.resolve()
    actual: dict[str, Path] = {}
    unexpected: list[str] = []
    for path in sorted(p for p in skill_root.rglob("*") if p.is_file()):
        rel = path.relative_to(skill_root).as_posix()
        if any(part in IGNORED_PARTS for part in path.relative_to(skill_root).parts):
            continue
        if rel not in ALLOWLIST:
            unexpected.append(rel)
        else:
            actual[rel] = path
    missing = sorted(ALLOWLIST - actual.keys())
    if missing or unexpected:
        messages = []
        if missing:
            messages.append(f"missing allowlisted files: {missing}")
        if unexpected:
            messages.append(f"unexpected files outside allowlist: {unexpected}")
        raise ValidationError("; ".join(messages))
    return actual


def build_package(skill_root: Path, output: Path) -> dict:
    skill_root = skill_root.resolve()
    if skill_root.name != "taleb-options-research":
        raise ValidationError(f"unexpected Skill directory name: {skill_root}")
    validate_release(skill_root / "references")
    files = collect_files(skill_root)

    output = output.expanduser().resolve()
    if output.suffix.lower() != ".zip":
        output = output / "taleb-options-research-1.1.0.zip"
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="taleb-options-public-") as temp_name:
        temp_root = Path(temp_name)
        package_root = temp_root / "taleb-options-research"
        for rel, source in files.items():
            destination = package_root / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

        findings = scan_tree(package_root)
        if findings:
            raise ValidationError("pre-package scan failed:\n" + "\n".join(findings))

        entries = [
            {
                "path": rel,
                "size_bytes": (package_root / rel).stat().st_size,
                "sha256": sha256_file(package_root / rel),
            }
            for rel in sorted(files)
        ]
        package_manifest = {
            "schema_version": "1.0",
            "package": "taleb-options-research",
            "release_version": "1.1.0",
            "entries": entries,
            "excluded": "third-party sources, OCR, images, audio, caches, credentials, and local paths",
        }
        write_json(package_root / "PACKAGE-MANIFEST.json", package_manifest)

        if output.exists():
            output.unlink()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(p for p in package_root.rglob("*") if p.is_file()):
                info = zipfile.ZipInfo(
                    path.relative_to(temp_root).as_posix(),
                    date_time=(1980, 1, 1, 0, 0, 0),
                )
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                archive.writestr(info, path.read_bytes())

        extract_root = temp_root / "extracted"
        with zipfile.ZipFile(output) as archive:
            for member in archive.infolist():
                member_path = Path(member.filename)
                if member_path.is_absolute() or ".." in member_path.parts:
                    raise ValidationError(f"unsafe archive member: {member.filename}")
            archive.extractall(extract_root)

        extracted_skill = extract_root / "taleb-options-research"
        findings = scan_tree(extracted_skill)
        if findings:
            raise ValidationError(
                "post-extraction scan failed:\n" + "\n".join(findings)
            )
        extracted_manifest = json.loads(
            (extracted_skill / "PACKAGE-MANIFEST.json").read_text(encoding="utf-8")
        )
        for entry in extracted_manifest["entries"]:
            path = extracted_skill / entry["path"]
            if sha256_file(path) != entry["sha256"]:
                raise ValidationError(f"post-extraction hash mismatch: {entry['path']}")

    return {
        "zip": str(output),
        "sha256": sha256_file(output),
        "files": len(files) + 1,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skill-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        result = build_package(args.skill_root, args.output)
    except (ValidationError, OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
    print(f"PASS: {result}")
