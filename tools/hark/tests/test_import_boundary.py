"""D1: Pipecat is imported only under hark/audio/. Everything else stays framework-free."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = ROOT / "hark" / "audio"


def _imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names


def test_only_hark_audio_imports_pipecat():
    offenders = [
        str(path.relative_to(ROOT))
        for path in sorted((ROOT / "hark").rglob("*.py")) + sorted((ROOT / "tests").rglob("*.py"))
        if not path.is_relative_to(ALLOWED)
        and any(name == "pipecat" or name.startswith("pipecat.") for name in _imports(path))
    ]
    assert offenders == [], f"pipecat imported outside hark/audio/: {offenders}"


def test_the_check_sees_pipecat_imports(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_text("from pipecat.frames.frames import Frame\nimport pipecat\n")
    assert {"pipecat", "pipecat.frames.frames"} <= _imports(bad)
