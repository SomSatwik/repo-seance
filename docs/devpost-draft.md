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
- Ollama installed (0.40.13) at C:\Users\ssoms\AppData\Local\Programs\Ollama\. Server running on localhost:11434.
- `gemma2:2b` pull IN PROGRESS (~99 MB / 1.6 GB at ~3 MB/s, ~8 min remaining). Not 9B — fits 6GB VRAM.
- Built `apps/api/agent/client.py` thin wrapper over Ollama `/api/generate`: `generate(prompt, context)` with model from `OLLAMA_MODEL` env var. Also has `embed()` and `status()`.
- Added `GET /system/status` reporting model name, inference mode (GPU/CPU via Ollama `/api/ps`), and Ollama reachability — not hardcoded. Endpoint returns `ollama_reachable:false` until Gemma is loaded.
- Real test call to Gemma: PENDING (blocked on Gemma download).
- `OLLAMA_MODEL=gemma2:2b` configured in `.env`.
- **Technical decision**: `/api/generate` over `/api/chat` for simplicity; single-turn prompts don't need conversation state today.

### Part C — Evidence retrieval
- Embedding model: `nomic-embed-text` via Ollama embedding API (small, fast, local).
- Alembic migration `0002` added `evidence` table with pgvector column: repo_id, content, source_type, source_ref, embedding.
- `retrieve_evidence(query, repo_id, k=5)` does cosine similarity via pgvector `<=>` operator.
- Indexed commit messages + README + top-level file docstrings.
- **Technical decision**: single table with `source_type` discriminator (commit/readme/file) rather than separate tables — keeps schema minimal and query uniform.

### Part D — Grounded Q&A + recovery roadmap
- `POST /repos/{id}/ask` — retrieves evidence via pgvector, builds Gemma prompt with actual file paths/commit hashes, requires citations.
- `POST /repos/{id}/roadmap` — prioritized recovery roadmap grounded in activity gap + contributor stats + TODO/FIXME from structure scan.
- [ ] Verified answers contain real file paths/commit hashes from retrieval (NOT plausible-sounding prose).
- **Technical decision**: citations appended as bracketed refs `[commit:abc123]` / `[file:src/foo.py]` parsed from retrieved rows.

### Minimal dashboard
- [ ] Next.js page: repo URL input → ingestion status → tabs (Architecture, History, Ask, Roadmap). No interactive graph (Sprint 2).

### Latency numbers (Gemma 2B)
- generate(): [BLOCKED — Ollama install download repeatedly fails (connection aborted by host); will retry. Gemma 2B not yet pulled.]
- embed: [BLOCKED — same]

### Push checkpoints
- [x] Pushed to GitHub at natural checkpoints: `bb28dc3` (Sprint 1 core: history + agent + retrieval + ask/roadmap) — https://github.com/SomSatwik/repo-seance
