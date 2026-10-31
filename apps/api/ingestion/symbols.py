"""Tree-sitter symbol extraction (top-level functions, classes, imports)."""

from pathlib import Path

import tree_sitter_languages

# Extension -> tree-sitter language name for symbol extraction.
TREE_SITTER_BY_EXT = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
}

CAPTURES = {
    "python": {
        "function_definition": "function",
        "class_definition": "class",
        "import_statement": "import",
        "import_from_statement": "import",
    },
    "javascript": {
        "function_declaration": "function",
        "class_declaration": "class",
        "import_statement": "import",
    },
    "typescript": {
        "function_declaration": "function",
        "class_declaration": "class",
        "interface_declaration": "interface",
        "type_alias_declaration": "type",
        "import_statement": "import",
    },
    "tsx": {
        "function_declaration": "function",
        "class_declaration": "class",
        "interface_declaration": "interface",
        "type_alias_declaration": "type",
        "import_statement": "import",
    },
}

_MAX_SYMBOLS = 2000


def extract_symbols(path: Path, language: str) -> list[dict]:
    """Extract top-level symbols from a source file using tree-sitter.

    Returns a list of ``{"kind", "name", "line"}`` dicts (empty on failure).
    """
    captures = CAPTURES.get(language)
    if not captures:
        return []
    try:
        parser = tree_sitter_languages.get_parser(language)
    except Exception:  # noqa: BLE001 - unsupported language
        return []
    try:
        code = path.read_bytes()
    except OSError:
        return []
    tree = parser.parse(code)
    out: list[dict] = []
    _walk(tree.root_node, captures, out, _MAX_SYMBOLS)
    return out


def _walk(node, captures: dict, out: list, limit: int) -> None:
    kind = captures.get(node.type)
    if kind is not None:
        out.append({"kind": kind, "name": _name(node), "line": _line(node)})
        if len(out) >= limit:
            return
    for child in node.children:
        _walk(child, captures, out, limit)
        if len(out) >= limit:
            return


def _name(node) -> str | None:
    field = node.child_by_field_name("name")
    if field is not None:
        return _text(field)
    for child in node.children:
        if child.is_named:
            return _text(child)
    return _text(node)


def _line(node) -> int | None:
    try:
        return node.start_point[0] + 1
    except Exception:  # noqa: BLE001
        try:
            return node.start_point.row + 1
        except Exception:  # noqa: BLE001
            return None


def _text(node) -> str:
    data = node.text
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    return data
