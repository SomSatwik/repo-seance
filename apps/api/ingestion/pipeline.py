"""End-to-end ingestion: clone -> scan -> persist file/symbol rows."""

from pathlib import Path

from config import settings
from models import File
from .clone import remove_tree, clone_repo
from .structure import collect_files, scan_structure
from .symbols import TREE_SITTER_BY_EXT, extract_symbols


def run_ingestion(repo_id: int, url: str, db) -> dict:
    """Clone a repo, scan it, persist per-file rows, and return the summary.

    ``db`` is a SQLAlchemy session; rows are flushed (not committed) so the
    caller controls the transaction boundary.
    """
    dest = settings.data_dir / "repos" / str(repo_id)
    try:
        clone_repo(url, dest)
        summary = scan_structure(dest, settings.max_tree_depth, settings.max_files)
        for rel, lang in collect_files(dest, settings.max_files):
            ts_lang = TREE_SITTER_BY_EXT.get(Path(rel).suffix.lower())
            symbols = extract_symbols(dest / rel, ts_lang) if ts_lang else []
            db.add(File(repo_id=repo_id, path=rel, language=lang, symbols=symbols))
        db.flush()
        return summary
    except Exception:
        remove_tree(dest)
        raise
