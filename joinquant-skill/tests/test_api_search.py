"""Tests for scripts/api_search.py."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _run_search(*args: str) -> tuple[int, str, str]:
    """Run api_search.py and return (returncode, stdout, stderr)."""
    import subprocess
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / 'scripts' / 'api_search.py'), *args],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    return result.returncode, result.stdout, result.stderr


def test_search_finds_known_function() -> None:
    """Searching for a known API function should succeed."""
    code, stdout, stderr = _run_search('get_price')
    assert code == 0, f'Search failed: {stderr}'
    assert 'Found' in stdout
    assert 'get_price' in stdout.lower() or 'get_price' in stderr.lower()


def test_search_returns_nonzero_for_no_match() -> None:
    """Searching for a nonsense string should fail."""
    code, stdout, stderr = _run_search('zzz_nonexistent_function_xyz_12345')
    assert code != 0
    assert 'No match' in stderr


def test_search_with_regex_flag() -> None:
    """--regex flag should work and find pattern matches."""
    code, stdout, stderr = _run_search('--regex', 'set_\\w+', '-n', '5')
    assert code == 0, f'Regex search failed: {stderr}'
    assert 'Found' in stdout


def test_search_with_context_flag() -> None:
    """--context flag should show surrounding lines."""
    code, stdout, stderr = _run_search('--context', '5', 'set_benchmark')
    assert code == 0
    # With context=5 we should see more lines around the match
    assert 'set_benchmark' in stdout.lower() or 'set_benchmark' in stderr.lower()
