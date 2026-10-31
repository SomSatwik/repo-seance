"""Repository structure scanning: file tree, extension counts, languages, manifests."""

import json
import tomllib
from collections import Counter
from pathlib import Path

from config import settings

LANG_BY_EXT = {
    ".py": "Python",
    ".pyw": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".rs": "Rust",
    ".go": "Go",
    ".java": "Java",
    ".kt": "Kotlin",
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hpp": "C++",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".sh": "Shell",
    ".bash": "Shell",
    ".md": "Markdown",
    ".json": "JSON",
    ".toml": "TOML",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sql": "SQL",
    ".txt": "Text",
    ".xml": "XML",
    ".csv": "CSV",
    ".mk": "Makefile",
}

# Config/manifest filenames -> language hint.
_CONFIG_HINTS = {
    "package.json": "JavaScript",
    "pyproject.toml": "Python",
    "requirements.txt": "Python",
    "setup.py": "Python",
    "Pipfile": "Python",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
    "Gemfile": "Ruby",
    "composer.json": "PHP",
}

MANIFEST_FILES = {
    "package.json",
    "pyproject.toml",
    "Cargo.toml",
    "requirements.txt",
    "go.mod",
    "Gemfile",
    "composer.json",
    "Pipfile",
}

_SHEBANG_MAP = {
    "python": "Python",
    "python3": "Python",
    "node": "JavaScript",
    "nodejs": "JavaScript",
    "bash": "Shell",
    "sh": "Shell",
    "zsh": "Shell",
    "ruby": "Ruby",
    "perl": "Perl",
    "php": "PHP",
}

_IGNORED_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}


def detect_language(path: Path) -> str | None:
    """Detect a file's language by extension, config-file name, then shebang."""
    if path.name in _CONFIG_HINTS:
        return _CONFIG_HINTS[path.name]
    ext = path.suffix.lower()
    if ext in LANG_BY_EXT:
        return LANG_BY_EXT[ext]
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as fh:
            first = fh.readline()
        if first.startswith("#!"):
            parts = first[2:].strip().split()
            interp = Path(parts[0]).name if parts else ""
            if interp in _SHEBANG_MAP:
                return _SHEBANG_MAP[interp]
            if "python" in interp:
                return "Python"
            if "node" in interp:
                return "JavaScript"
    except OSError:
        pass
    return None


def _iter_files(repo_path: Path, max_files: int):
    count = 0
    for p in sorted(repo_path.rglob("*")):
        if count >= max_files:
            break
        if not p.is_file():
            continue
        rel_parts = p.relative_to(repo_path).parts
        if any(part in _IGNORED_DIRS for part in rel_parts):
            continue
        count += 1
        yield p


def collect_files(
    repo_path: Path, max_files: int | None = None
) -> list[tuple[str, str | None]]:
    """Return ``[(relative_path, language)]`` for every file in the repo."""
    limit = max_files or settings.max_files
    out = []
    for p in _iter_files(repo_path, limit):
        out.append((p.relative_to(repo_path).as_posix(), detect_language(p)))
    return out


def scan_structure(
    repo_path: Path,
    max_depth: int | None = None,
    max_files: int | None = None,
) -> dict:
    """Produce a structured summary of a cloned repository."""
    depth = max_depth or settings.max_tree_depth
    limit = max_files or settings.max_files

    ext_counts: Counter = Counter()
    languages: set = set()
    manifests: dict = {}
    files_seen = 0

    for p in _iter_files(repo_path, limit):
        files_seen += 1
        rel = p.relative_to(repo_path).as_posix()
        ext = p.suffix.lower()
        if ext:
            ext_counts[ext] += 1
        lang = detect_language(p)
        if lang:
            languages.add(lang)
        if p.name in MANIFEST_FILES:
            parsed = _parse_manifest(p)
            if parsed is not None:
                manifests[rel] = parsed

    return {
        "file_count": files_seen,
        "file_tree": _build_tree(repo_path, depth),
        "extensions": dict(sorted(ext_counts.items())),
        "languages": sorted(languages),
        "manifests": manifests,
    }


def _build_tree(repo_path: Path, max_depth: int, max_per_dir: int = 200) -> dict:
    def _node(path: Path, depth: int) -> object:
        entries: dict = {}
        try:
            children = sorted(path.iterdir(), key=lambda c: c.name.lower())
        except OSError:
            return entries
        shown = 0
        for child in children:
            if child.name in _IGNORED_DIRS:
                continue
            if shown >= max_per_dir:
                entries["...(more)"] = None
                break
            if child.is_dir():
                entries[child.name + "/"] = (
                    _node(child, depth + 1) if depth < max_depth else "(truncated)"
                )
            else:
                entries[child.name] = None
            shown += 1
        return entries

    return _node(repo_path, 0)


def _parse_manifest(path: Path) -> dict | None:
    name = path.name
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    if name == "package.json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return {"_error": "invalid JSON"}
        return {
            "name": data.get("name"),
            "dependencies": data.get("dependencies", {}),
            "devDependencies": data.get("devDependencies", {}),
        }

    if name in ("pyproject.toml", "Cargo.toml"):
        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError:
            return {"_error": "invalid TOML"}
        if name == "pyproject.toml":
            project = data.get("project", {})
            deps = project.get("dependencies", []) or []
            if isinstance(deps, list):
                deps = [d if isinstance(d, str) else str(d) for d in deps]
            poetry = data.get("tool", {}).get("poetry", {})
            return {
                "project": {"name": project.get("name"), "dependencies": deps},
                "poetry": {"dependencies": list(poetry.get("dependencies", {}).keys())},
            }
        return {
            "package": data.get("package", {}).get("name"),
            "dependencies": list(data.get("dependencies", {}).keys()),
            "dev_dependencies": list(data.get("dev-dependencies", {}).keys()),
        }

    if name == "requirements.txt":
        reqs = []
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("-"):
                reqs.append(line.split("#", 1)[0].strip())
        return {"requirements": reqs}

    if name == "go.mod":
        for line in text.splitlines():
            if line.strip().startswith("module "):
                return {"module": line.strip().split(" ", 1)[1]}
        return {"module": None}

    if name == "Gemfile":
        gems = [l.strip() for l in text.splitlines() if l.strip().startswith("gem ")]
        return {"gems": gems}

    if name == "composer.json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return {"_error": "invalid JSON"}
        return {"name": data.get("name"), "require": data.get("require", {})}

    if name == "Pipfile":
        return {"_raw": text[:500]}

    return {"_raw": text[:500]}
