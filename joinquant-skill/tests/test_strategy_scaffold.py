"""Tests for scripts/strategy_scaffold.py."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.strategy_scaffold import TEMPLATE_MAP, list_templates


def test_template_map_has_all_types() -> None:
    """Every advertised strategy type should map to a real template file."""
    for alias, filename in TEMPLATE_MAP.items():
        path = PROJECT_ROOT / 'templates' / filename
        assert path.exists(), f'Template {filename} (alias {alias}) not found'


def test_template_map_no_duplicate_canonical_names() -> None:
    """Canonical template filenames should be unique."""
    canonical = set(TEMPLATE_MAP.values())
    assert len(canonical) == len(set(TEMPLATE_MAP.values()))


@pytest.mark.parametrize('type_name', [
    'basic', 'multi-factor', 'rotation', 'momentum', 'mean-reversion',
])
def test_scaffold_generates_output(tmp_path: Path, type_name: str) -> None:
    """--type with --output should produce a .py file."""
    import subprocess
    out = tmp_path / f'{type_name}.py'
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / 'scripts' / 'strategy_scaffold.py'),
         '--type', type_name, '--output', str(out)],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, f'scaffold failed for {type_name}: {result.stderr}'
    assert out.exists(), f'Output file not created for {type_name}'
    content = out.read_text(encoding='utf-8')
    assert 'def initialize' in content, f'Generated {type_name} missing initialize()'
    assert 'set_benchmark' in content, f'Generated {type_name} missing set_benchmark'


def test_scaffold_list_mode(capsys: pytest.CaptureFixture) -> None:
    """--list should print template names without error."""
    import subprocess
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / 'scripts' / 'strategy_scaffold.py'), '--list'],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0
    assert '01-basic-single-stock.py' in result.stdout
    assert '05-mean-reversion.py' in result.stdout


def test_scaffold_unknown_type_fails() -> None:
    """An unknown --type should exit with error."""
    import subprocess
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / 'scripts' / 'strategy_scaffold.py'),
         '--type', 'nonexistent'],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    assert result.returncode != 0


def test_scaffold_security_override(tmp_path: Path) -> None:
    """--security should replace the default security in generated output."""
    import subprocess
    out = tmp_path / 'custom.py'
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / 'scripts' / 'strategy_scaffold.py'),
         '--type', 'basic', '--security', '510300.XSHG', '--output', str(out)],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0
    content = out.read_text(encoding='utf-8')
    assert "510300.XSHG" in content, 'Security override not applied'
