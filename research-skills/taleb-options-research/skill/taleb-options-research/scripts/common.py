#!/usr/bin/env python3
"""Shared, offline helpers for the Taleb options research Skill."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

RELEASE_FILES = {
    "claims": "claim-registry.release.jsonl",
    "formulas": "formula-registry.release.jsonl",
    "visuals": "visual-registry.release.jsonl",
    "rules": "rule-registry.release.jsonl",
}

BASELINE_MIN_COUNTS = {
    "claims": 397,
    "formulas": 223,
    "visuals": 237,
    "rules": 171,
}

FORBIDDEN_EXTENSIONS = {
    ".pdf",
    ".epub",
    ".djvu",
    ".mp3",
    ".m4a",
    ".wav",
    ".png",
    ".jpg",
    ".jpeg",
}

WINDOWS_ABSOLUTE_RE = re.compile(r"(?i)(?:[a-z]:\\(?:users|documents|temp|tmp)\\)")
UNIX_ABSOLUTE_RE = re.compile(r"(?<![:\w])/(?:home|users|tmp|var|etc)/")
SECRET_PATTERNS = {
    "OpenAI-style key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "GitHub classic token": re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    "GitHub fine-grained token": re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}


class ValidationError(ValueError):
    """Raised when a public artifact violates a deterministic contract."""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(row, dict):
            raise ValidationError(f"{path}:{line_number}: expected an object")
        rows.append(row)
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
        for row in rows
    )
    path.write_text(text, encoding="utf-8", newline="\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def scan_text(text: str) -> list[str]:
    findings: list[str] = []
    if WINDOWS_ABSOLUTE_RE.search(text):
        findings.append("Windows absolute local path")
    if UNIX_ABSOLUTE_RE.search(text):
        findings.append("Unix absolute local path")
    for label, pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            findings.append(label)
    return findings


def scan_tree(root: Path) -> list[str]:
    findings: list[str] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        if path.suffix.lower() in FORBIDDEN_EXTENSIONS:
            findings.append(f"{rel}: forbidden extension")
            continue
        if path.name.lower() in {".env", "credentials", "credentials.json"}:
            findings.append(f"{rel}: forbidden credential filename")
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append(f"{rel}: unexpected binary file")
            continue
        findings.extend(f"{rel}: {finding}" for finding in scan_text(text))
    return findings


def require_keys(row: dict[str, Any], keys: Iterable[str], label: str) -> None:
    missing = [key for key in keys if key not in row]
    if missing:
        raise ValidationError(f"{label}: missing keys {', '.join(missing)}")
