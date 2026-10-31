"""Ingestion integration tests against a real git clone."""

import json
import subprocess
from pathlib import Path

import pytest

from ingestion.clone import CloneError, clone_repo
from ingestion.structure import scan_structure
from ingestion.symbols import extract_symbols

FIXTURE_FILES = {
    "hello.py": (
        '"""A tiny Python module."""\n'
        "import os\n\n"
        "def greet(name: str) -> str:\n"
        '    return f"hello {name}"\n\n'
        "class Greeter:\n"
        "    def __init__(self, name):\n"
        "        self.name = name\n"
        "    def greet(self):\n"
        "        return greet(self.name)\n"
    ),
    "app.js": (
        "export function add(a, b) {\n"
        "  return a + b;\n"
        "}\n\n"
        "export class Calculator {\n"
        "  multiply(a, b) {\n"
        "    return a * b;\n"
        "  }\n"
        "}\n"
    ),
    "util.ts": (
        "export interface Config {\n"
        "  name: string;\n"
        "}\n\n"
        "export function format(x: string): string {\n"
        "  return x.trim();\n"
        "}\n\n"
        "export class Util {\n"
        "  static upper(s: string) {\n"
        "    return s.toUpperCase();\n"
        "  }\n"
        "}\n"
    ),
    "package.json": json.dumps(
        {"name": "fixture", "dependencies": {"react": "^19.0.0"}}
    ),
    "pyproject.toml": '[project]\nname = "fixture"\ndependencies = ["requests>=2.0"]\n',
    "requirements.txt": "requests==2.32.0\nflask==3.0.0\n",
    "README.md": "# fixture\n",
}


@pytest.fixture()
def fixture_repo(tmp_path: Path) -> Path:
    """Create a real local git repo with a known set of files, then commit it."""
    repo = tmp_path / "fixture"
    repo.mkdir()
    for name, content in FIXTURE_FILES.items():
        (repo / name).write_text(content, encoding="utf-8")
    (repo / "src").mkdir()
    (repo / "src" / "nested.py").write_text("def nested():\n    return 1\n", encoding="utf-8")

    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)
    return repo


def test_clone_and_structure(fixture_repo: Path, tmp_path: Path) -> None:
    dest = tmp_path / "clone"
    clone_repo(fixture_repo.as_uri(), dest)

    summary = scan_structure(dest)

    # 7 root files + src/nested.py = 8 files
    assert summary["file_count"] == 8
    assert summary["extensions"][".py"] == 2
    assert summary["extensions"][".js"] == 1
    assert summary["extensions"][".ts"] == 1
    assert "Python" in summary["languages"]
    assert "JavaScript" in summary["languages"]
    assert "TypeScript" in summary["languages"]

    assert "package.json" in summary["manifests"]
    assert summary["manifests"]["package.json"]["dependencies"]["react"] == "^19.0.0"
    assert "pyproject.toml" in summary["manifests"]
    assert "requirements.txt" in summary["manifests"]
    assert summary["manifests"]["requirements.txt"]["requirements"] == [
        "requests==2.32.0",
        "flask==3.0.0",
    ]


def test_size_limit_rejects_and_removes_clone(tmp_path: Path) -> None:
    """Exceeding the size limit raises and leaves nothing behind on disk."""
    repo = tmp_path / "big"
    repo.mkdir()
    (repo / "blob.bin").write_bytes(b"x" * (2 * 1024 * 1024))
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)

    dest = tmp_path / "clone"
    with pytest.raises(CloneError, match="exceeding the"):
        clone_repo(repo.as_uri(), dest, max_size_mb=1)
    assert not dest.exists()


def test_symbol_extraction(fixture_repo: Path, tmp_path: Path) -> None:
    dest = tmp_path / "clone"
    clone_repo(fixture_repo.as_uri(), dest)

    py_syms = extract_symbols(dest / "hello.py", "python")
    py_kinds = {s["kind"] for s in py_syms}
    assert "function" in py_kinds
    assert "class" in py_kinds
    assert "import" in py_kinds

    js_syms = extract_symbols(dest / "app.js", "javascript")
    js_kinds = {s["kind"] for s in js_syms}
    assert "function" in js_kinds
    assert "class" in js_kinds

    ts_syms = extract_symbols(dest / "util.ts", "typescript")
    ts_kinds = {s["kind"] for s in ts_syms}
    assert "function" in ts_kinds
    assert "class" in ts_kinds
    assert "interface" in ts_kinds
