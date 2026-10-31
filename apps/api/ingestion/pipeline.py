"""End-to-end ingestion: clone -> scan -> persist file/symbol rows + history + evidence."""

from pathlib import Path

from agent.retrieval import index_text
from config import settings
from history.analyzer import get_commit_log, get_contributor_stats, detect_activity_gaps
from models import Commit, File
from .clone import remove_tree, clone_repo
from .structure import collect_files, scan_structure
from .symbols import TREE_SITTER_BY_EXT, extract_symbols


def _persist_commits(db, repo_id: int, repo_path: Path) -> dict:
    """Read git history and persist commit rows; return summary stats."""
    commits = get_commit_log(repo_path)
    for c in commits:
        db.add(
            Commit(
                repo_id=repo_id,
                hash=c.hash,
                short_hash=c.short_hash,
                author=c.author,
                author_email=c.author_email,
                date=c.date,
                message=c.message,
                files_changed=c.files_changed,
            )
        )
    db.flush()
    stats = get_contributor_stats(repo_path)
    gap = detect_activity_gaps(repo_path)
    return {
        "commit_count": len(commits),
        "contributors": len(stats),
        "gap_days": gap.days,
        "gap_message": gap.message,
    }


def _index_evidence(db, repo_id: int, repo_path: Path, commits) -> None:
    """Embed and store searchable evidence: commit messages, README, top-level file docstrings.

    Best-effort: if Ollama isn't available yet, ingestion still completes
    (commits + files are stored) but embeddings are skipped. The /ask and
    /roadmap endpoints will report no evidence until Ollama is up.
    """
    try:
        from agent.retrieval import index_text
    except Exception:
        return

    # Commit messages as evidence.
    for c in commits[:200]:
        try:
            index_text(
                db,
                repo_id,
                source_type="commit",
                source_ref=c.short_hash,
                content=f"{c.author}: {c.message}",
            )
        except Exception:  # noqa: BLE001 - Ollama may be down
            break

    # README content.
    for readme_name in ("README.md", "README.rst", "README.txt", "README"):
        readme_path = repo_path / readme_name
        if readme_path.exists():
            try:
                content = readme_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                content = ""
            if content.strip():
                try:
                    index_text(
                        db,
                        repo_id,
                        source_type="readme",
                        source_ref=readme_name,
                        content=content[:4000],
                    )
                except Exception:  # noqa: BLE001 - Ollama may be down
                    pass
            break

    # Top-level source file docstrings / summaries.
    top_level = sorted(
        p for p in repo_path.iterdir()
        if p.is_file() and p.suffix.lower() in {".py", ".js", ".ts", ".tsx", ".go", ".rs"}
    )
    for f in top_level[:25]:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        summary = _file_summary(text)
        if summary:
            try:
                index_text(
                    db,
                    repo_id,
                    source_type="file",
                    source_ref=f.name,
                    content=summary,
                )
            except Exception:  # noqa: BLE001 - Ollama may be down
                pass


def _file_summary(text: str) -> str:
    """Extract a short summary: module docstring or first meaningful lines."""
    stripped = text.strip()
    if stripped.startswith('"""') or stripped.startswith("'''"):
        end = stripped.find(stripped[:3], 3)
        if end != -1:
            return stripped[: end + 3]
        return stripped[:500]
    # Fall back to first non-blank, non-import lines.
    lines = [l for l in stripped.splitlines() if l.strip() and not l.startswith(("import ", "from "))]
    return "\n".join(lines[:8])[:500]


def run_ingestion(repo_id: int, url: str, db) -> dict:
    """Clone a repo, scan it, persist per-file rows, history, evidence, and return the summary.

    ``db`` is a SQLAlchemy session; rows are flushed (not committed) so the
    caller controls the transaction boundary.
    """
    dest = settings.data_dir / "repos" / str(repo_id)
    try:
        clone_repo(url, dest)
        summary = scan_structure(dest, settings.max_tree_depth, settings.max_files)
        commits = get_commit_log(dest)
        history = _persist_commits_from_records(db, repo_id, commits)
        _index_evidence(db, repo_id, dest, commits)
        for rel, lang in collect_files(dest, settings.max_files):
            ts_lang = TREE_SITTER_BY_EXT.get(Path(rel).suffix.lower())
            symbols = extract_symbols(dest / rel, ts_lang) if ts_lang else []
            db.add(File(repo_id=repo_id, path=rel, language=lang, symbols=symbols))
        db.flush()
        summary["history"] = history
        return summary
    except Exception:
        remove_tree(dest)
        raise


def _persist_commits_from_records(db, repo_id: int, commits) -> dict:
    """Persist a list of CommitRecord objects; return summary stats."""
    for c in commits:
        db.add(
            Commit(
                repo_id=repo_id,
                hash=c.hash,
                short_hash=c.short_hash,
                author=c.author,
                author_email=c.author_email,
                date=c.date,
                message=c.message,
                files_changed=c.files_changed,
            )
        )
    db.flush()
    stats = get_contributor_stats_from_records(commits)
    gap = detect_activity_gaps_from_records(commits)
    return {
        "commit_count": len(commits),
        "contributors": len(stats),
        "gap_days": gap.days,
        "gap_message": gap.message,
    }


def get_contributor_stats_from_records(commits):
    from collections import defaultdict
    by_author = defaultdict(lambda: {"commit_count": 0, "first": None, "last": None, "author": ""})
    for c in commits:
        e = by_author[c.author_email]
        e["commit_count"] += 1
        e["author"] = c.author
        if e["first"] is None or c.date < e["first"]:
            e["first"] = c.date
        if e["last"] is None or c.date > e["last"]:
            e["last"] = c.date
    return list(by_author.values())


def detect_activity_gaps_from_records(commits):
    from dataclasses import make_dataclass
    Gap = make_dataclass("Gap", ["days", "message"])
    if len(commits) < 2:
        return Gap(0.0, "Not enough history to detect a gap.")
    dates = sorted([c.date for c in commits], reverse=True)
    max_gap = 0.0
    gs = ge = None
    for i in range(len(dates) - 1):
        delta = (dates[i] - dates[i + 1]).total_seconds()
        if delta > max_gap:
            max_gap = delta
            ge = dates[i]
            gs = dates[i + 1]
    days = max_gap / 86400.0
    msg = f"Development gap of {days:.1f} days ({gs:%Y-%m-%d} -> {ge:%Y-%m-%d})." if gs and ge else "No activity gap detected."
    return Gap(days, msg)

