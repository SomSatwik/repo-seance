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

## Sprint 2: GhostTrace — Terminal Companion + Horror Identity

### Part A — Deterministic safety engine (`apps/api/ghosttrace/safety_rules.py`)
- Rule-based (NOT LLM-based) shell command classifier using regex with word boundaries.
- Classifies commands: SAFE / CAUTION / DESTRUCTIVE.
- DESTRUCTIVE patterns: `rm -rf/fr`, `rd /s`, `git reset --hard`, `git push --force/-f`, `git clean -fdx`, `DROP TABLE/DATABASE`, `TRUNCATE`, `chmod -R 777`, `curl|sh`, `wget|bash`, `dd of=/dev/`.
- CAUTION patterns: plain `rm`, `git reset` (no --hard), `git checkout/switch`, `chmod`, `mv`, redirect overwrite, `dd`, `git clean`.
- Unit tests (`tests/test_safety_rules.py`, 69 cases) cover positive matches AND negative "looks similar but isn't" cases (`rm -ri`, `git reset --soft`, `git push` plain, `chmod 755`, `rmdir`, etc.). ALL PASS.
- Aggressive-by-design: `DROP TABLE` flagged even in comments (missed destructive > false positive).
- Works with zero LLM calls — module imports only `re`/`dataclasses`, confirmed by running tests with Ollama stopped.


### Part B — Command interception + contextual explanation (`apps/api/ghosttrace/router.py`)
- WebSocket endpoint `/ws/ghosttrace?repo_id={id}` — client sends a command, server returns safety classification + Gemma explanation.
- Safety verdict computed by deterministic engine BEFORE any LLM call — Gemma only explains, never second-guesses (enforced in code structure).
- Gemma pulls real context from Sprint 1's evidence/history layer (commit hashes, file paths) for grounded explanations.
- Explicitly opt-in via `GHOSTTRACE_ENABLED` and project-scoped via `GHOSTTRACE_PROJECT_SCOPE_ONLY` — only sees current repo, not the whole machine.
- Verified with real commands: safe (`ls -la`), caution (`rm old_note.txt`), destructive (`rm -rf ./build`, `git reset --hard HEAD`) — all explanations cite real commit `7fd1a60b`.


### Part C — Horror visual identity (`apps/web/app/ghosttrace/`)
- Distinct terminal-style view, separate feel from clean Repo Séance dashboard.
- Palette: near-black `#050505` bg, blood-red `#B5121B` accent, Geist_Mono monospace throughout.
- Custom original ASCII logo (ghost heads + terminal cursor `||█||`), line-by-line startup reveal.
- CRT scanline + vignette overlay, flickering cursor, rare glitch on state changes (subtle, tested on second viewing).
- Warning states: DESTRUCTIVE = red animated pulse, CAUTION = amber pulse, SAFE = understated.
- Ghost-themed notification banner distinct from generic chat bubble.
- Working terminal: command input, scrollback, readable monospace output, live WebSocket status.
- Deliberate transition: homepage link "Open GhostTrace terminal" shifts tone without being jarring.
- `GHOSTTRACE_ENABLED` flag genuinely gates the feature (verified both states).

## Sprint 2b: Installable GhostTrace CLI

- Added `packages/ghosttrace-cli`, a Python package installed as the `ghosttrace` command.
- The CLI connects to the existing `/ws/ghosttrace` WebSocket and renders the backend's deterministic verdict and Gemma-grounded explanation; it contains no duplicated safety rules or explanation logic.
- Ported the horror identity to ANSI terminal output: blood-red DESTRUCTIVE, amber CAUTION, and understated dim SAFE, with the original ASCII logo revealed line by line.
- Kept both surfaces for distinct purposes: the web terminal is the browser-based demo/preview, while the CLI is the actual installable terminal product. They share the same backend and therefore the same safety behavior.

## Sprint 1 COMPLETE

All completion criteria met:
- [x] Real commit history stored and queryable, gap detection works on real repo
- [x] Gemma reachable via Ollama, model/inference-mode genuinely detected (CPU) not hardcoded
- [x] pgvector retrieval returns real evidence for a real query
- [x] `/ask` and `/roadmap` responses contain real citations from the repo (verified by reading actual output)
- [x] `docs/devpost-draft.md` has running notes from this sprint
- [x] Commits incremental, pushed to GitHub at natural checkpoints
