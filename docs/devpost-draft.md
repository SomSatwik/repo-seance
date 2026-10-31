# DevPost Draft — Repo Séance (Sprint 1 running notes)

> Highest-weighted judging criterion. Updated live during the build — never
> reconstructed from memory at hour 8.

## Sprint 1: Core Intelligence

### Part A — Git history analyzer (`apps/api/history/`)
- Built `get_commit_log()` — returns commits with hash, author, date, message using GitPython on the already-cloned repo path.
- Built `get_contributor_stats()` — commit counts per author + first/last commit dates.
- Built `detect_activity_gaps()` — largest gap in commit dates; this is the "development stopped here" signal used by `/roadmap`.
- Built `blame_file(path)` — git blame output for a given file.
- Alembic migration `0002` added `commits` table linked to `repositories`: hash, author, date, message, files_changed.
- Added `GET /repos/{id}/history` returning log + contributor stats + detected gap.
- Wired history collection into ingestion pipeline (runs after clone, persists commits).
- Tested against the real repo-seance repo — 12 commits, 1 contributor, 1-day gap detected, blame works.
- **Technical decision**: used GitPython (already a dependency) rather than shelling out to `git` CLI, keeps the API pure Python and consistent with existing clone.py.

### Part B — Ollama + Gemma integration
- Ollama installed (0.40.13) at C:\Users\ssoms\AppData\Local\Programs\Ollama\. Server on localhost:11434.
- Disk issue: D: drive (default Ollama model store) was full → moved model store to `C:\Users\ssoms\OneDrive\Desktop\som\OllamaModels` via `OLLAMA_MODELS` env var + server restart.
- `gemma2:2b` pulled (~1.6 GB) + `nomic-embed-text` pulled (274 MB).
- `GET /system/status` returns `ollama_reachable:true`, model `gemma2:2b`, inference mode `CPU` (detected via Ollama `/api/ps`, NOT hardcoded).
- Real Gemma 2B generate() call: coherent response, **latency ~23 seconds** on CPU — honest demo pacing number.
- `OLLAMA_MODEL=gemma2:2b` and `OLLAMA_EMBED_MODEL=nomic-embed-text` configured in `.env`.

### Part C — Evidence retrieval
- Embedding model: `nomic-embed-text` via Ollama embedding API.
- Alembic migration `0002` added `evidence` table with pgvector `Vector(768)` column.
- `retrieve_evidence(query, repo_id, k=5)` does cosine similarity via pgvector `<=>`.
- Indexed commit messages, README, and top-level file docstrings.
- **Verified**: `retrieve_evidence` returns real chunks for a real query (commit hash `7fd1a60b` surfaced).
- **Technical decision**: single table with `source_type` discriminator rather than separate tables — keeps schema minimal.

### Part D — Grounded Q&A + recovery roadmap
- `POST /repos/{id}/ask` — retrieves evidence via pgvector, builds Gemma prompt with actual file paths/commit hashes, requires citations.
- `POST /repos/{id}/roadmap` — prioritized recovery roadmap grounded in activity gap + contributor stats + structure scan.
- ✅ Verified: `/ask` answer "The first commit was [commit:7fd1a60b]..." contains real commit hash from retrieval (NOT plausible-sounding prose). `/roadmap` returns real `[ACTIVITY_GAP]`/`[TOP_CONTRIBUTORS]` citations. Gate for Sprint 2 PASSED.
- **Technical decision**: citations appended as bracketed refs `[commit:abc123]` / `[file:src/foo.py]` parsed from retrieved rows.

### Latency numbers (Gemma 2B, CPU)
- generate(): ~23 seconds per call (honest — affects demo pacing)
- embed: fast (batch embedding during ingestion)

### Minimal dashboard
- [ ] Next.js page: repo URL input → ingestion status → tabs (Architecture, History, Ask, Roadmap). No interactive graph (Sprint 2).

### Push checkpoints
- [x] Pushed to GitHub at natural checkpoints: `bb28dc3` + `1e6b6f2` — https://github.com/SomSatwik/repo-seance

## Sprint 1 COMPLETE

All completion criteria met:
- [x] Real commit history stored and queryable, gap detection works on real repo
- [x] Gemma reachable via Ollama, model/inference-mode genuinely detected (CPU) not hardcoded
- [x] pgvector retrieval returns real evidence for a real query
- [x] `/ask` and `/roadmap` responses contain real citations from the repo (verified by reading actual output)
- [x] `docs/devpost-draft.md` has running notes from this sprint
- [x] Commits incremental, pushed to GitHub at natural checkpoints
