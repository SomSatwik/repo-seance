# Repo Séance

```
  .-.
 ( o o )
  | O |
```

**Repository:** <https://github.com/SomSatwik/repo-seance>
**Live demo:** <https://counters-config-solo-kansas.trycloudflare.com/>
*(tunnels to my own machine — Gemma inference is genuinely running locally
on a GPU as you use it, not a hosted API. Live during Hacktoberfest judging;
if it's down, the setup steps below get you the same thing in a few minutes.)*

![Image description](https://dev-to-uploads.s3.us-east-2.amazonaws.com/uploads/articles/jr0thxk5ikqxa426vc2b.png)

![Image description](https://dev-to-uploads.s3.us-east-2.amazonaws.com/uploads/articles/ft0m4r4lbv8ddgjk09x6.png)

![Image description](https://dev-to-uploads.s3.us-east-2.amazonaws.com/uploads/articles/xhoepoblona2411bypsp.png)

> **Repo Séance** — summon the spirit of any git repository. A local,
> AI-powered forensic analyzer that ingests a codebase's full git history
> and lets you interrogate its ghosts in natural language — then carries
> that same evidence into your terminal.

Repo Séance reconstructs the "soul" of a repository — its commits,
contributors, and the stories embedded in its source — and makes it
searchable through a semantic, vector-backed memory. Point it at any git
repo and it will index the history, embed it locally, and answer questions
like *"who created this project and what was its original purpose?"* or
*"what changed before development stopped?"* — every answer cites the real
commit hashes and files it actually read, not a plausible guess.

**GhostTrace** is the second half of the project: a terminal companion that
uses that same evidence to explain unfamiliar or risky shell commands in
context. It's not a generic "this is dangerous" warning — it's grounded in
what Repo Séance actually found in *this* repository's history.

---

## What you can do

| | |
|---|---|
| **Ask the repository's ghosts** | `POST /repos/{id}/ask` — natural-language Q&A, every answer carries real `[commit:...]` / `[readme:...]` citations back to evidence in the repo. |
| **Generate a recovery roadmap** | `POST /repos/{id}/roadmap` — a prioritized plan grounded in the actual detected activity gap and top contributors, not generic advice. |
| **Inspect the git history** | Commit log, contributor leaderboard, and detected development-activity gaps for any ingested repository. |
| **Interrogate from the terminal** | `GhostTrace` classifies any shell command SAFE / CAUTION / DESTRUCTIVE with a deterministic rule engine, then explains the consequence using the repo's real history — e.g. flagging that `./build` hasn't been touched since the project went quiet. |
| **Run it as a real CLI** | `ghosttrace` installs as an actual terminal command (`pip install -e packages/ghosttrace-cli`), not just a web demo — same safety engine, same grounded explanations, in your real shell. |
| **See exactly what's running** | The model name, inference mode (GPU/CPU), and Ollama connectivity are surfaced directly in the app — never a hidden detail. |

The safety classification is **deterministic, not model-based** — it works
correctly with Ollama stopped entirely. Gemma only explains consequences
using retrieved evidence; it never decides whether a command is safe. That
split is a deliberate design choice, not a missing feature.

---

## Architecture

| Component      | Stack                                        | Port  |
| -------------- | -------------------------------------------- | ----- |
| Web UI         | Next.js (TypeScript, Tailwind, App Router)    | 3000  |
| API            | FastAPI (Python 3.12)                        | 8000  |
| Database       | Postgres 15 + pgvector (Docker)              | 5434  |
| Embeddings/LLM | Ollama (native Windows, GPU)                 | 11434 |
| GhostTrace CLI | Python, installable entry point (`ghosttrace`) | —   |

See [`docs/architecture.md`](docs/architecture.md) for the full diagram and
decision log.

## Prerequisites

- Docker Desktop (with Compose v5+)
- Python 3.12
- Node.js 20+ and pnpm 10+
- Ollama for local inference (GPU optional; `gemma2:2b` can run on CPU)

## Setup

### 1. Database (Postgres + pgvector)

```powershell
docker compose -f infra/docker-compose.yml up -d
```

Postgres listens on **localhost:5434** (chosen to avoid colliding with existing
dev containers on 5433). Verify it is healthy:

```powershell
docker compose -f infra/docker-compose.yml ps
```

### 2. API

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item ..\..\.env.example .env    # then adjust values as needed
uvicorn main:app --reload --port 8000
```

Health check: http://localhost:8000/health

### 3. Local models (Ollama)

Install Ollama for Windows from <https://ollama.com/download/windows>, start
the Ollama app/service, then download the models used by this project:

```powershell
ollama pull gemma2:2b
ollama pull nomic-embed-text
```

The API defaults to `gemma2:2b` for explanations and `nomic-embed-text` for
embeddings. Both run locally after their model weights are downloaded; an
NVIDIA GPU is optional. The tested RTX 4050 has 6 GB VRAM, so the 2B Gemma
model is the practical choice here. This machine reported CPU inference, with
about 23 seconds per generation in the recorded run.

The default `CLONE_DEPTH=0` keeps full history for the default branch. Set a
positive depth in `.env` to make shallow clones when faster, smaller imports
matter more than older history.

### 4. Web

```powershell
cd apps/web
pnpm install
pnpm dev
```

Open http://localhost:3000 — the homepage fetches the API `/health` endpoint live.

### 5. GhostTrace CLI (new — install it as a real terminal command)

With the API running and `GHOSTTRACE_ENABLED=true` set (see below), install
the CLI from the repo root:

```powershell
pip install -e packages/ghosttrace-cli
ghosttrace --repo <repo-id>
```

This gives you a real `ghosttrace` command on your `PATH` — type a shell
command and get back its SAFE / CAUTION / DESTRUCTIVE classification plus a
grounded explanation, directly in your terminal. It connects to the same
backend and evidence layer as the web version over WebSocket
(`ws://localhost:8000/ws/ghosttrace` by default; override with `--api-url`
for a remote deployment).

### GhostTrace (opt-in, backend flag)

Set `GHOSTTRACE_ENABLED=true` in the root `.env` to enable the project-scoped
GhostTrace endpoint. Keep `GHOSTTRACE_PROJECT_SCOPE_ONLY=true` to limit
retrieved context to the selected repository. GhostTrace never reads shell
history or files outside the selected project.

### Optional Sentry

Set `SENTRY_DSN` in the root `.env` to enable API error reporting and Ollama
generation spans (latency, model used, success/failure) across `/ask`,
`/roadmap`, and GhostTrace explanation calls. No DSN is required for local
development; Sentry is disabled when the setting is empty. Prompts and local
variables are not sent as Sentry event data.

## Render deployment

The root [`render.yaml`](render.yaml) is a Render Blueprint for the full app:
Next.js web service, FastAPI service, managed Postgres with pgvector, and a
private Ollama service running Gemma 2B plus `nomic-embed-text`. Repository
clones and Ollama model files use persistent disks so they survive service
restarts and deploys. The API's pre-deploy step runs Alembic migrations.

1. Push the repository to GitHub and create a Blueprint in the
   [Render Dashboard](https://dashboard.render.com/), selecting this repo and
   its `render.yaml`.
2. Review the Blueprint's monthly estimate before applying it. This setup
   uses paid compute, a managed database, and persistent disks; Ollama runs on
   CPU and may respond more slowly than the local GPU-backed setup.
3. After provisioning, open the web service and confirm its public API URL
   matches `NEXT_PUBLIC_API_URL` in the Blueprint. If Render assigns a
   different service subdomain, update that value and the API's
   `CORS_ORIGINS`, then redeploy.
4. Wait for the Ollama service to download both models before testing
   `/ask`, `/roadmap`, or GhostTrace. These model downloads are stored on its
   persistent disk.
   The installed CLI can then connect with
   `ghosttrace --api-url wss://reposeance-api.onrender.com --repo <repo-id>`.

The API is public and the current app has no user authentication or
rate-limiting; use this deployment for a demo, not for untrusted production
traffic. Public repository cloning also requires outbound internet access.

## Self-hosting with Coolify

For a single-VPS deployment, use
[`infra/docker-compose.coolify.yml`](infra/docker-compose.coolify.yml) with
Coolify's Docker Compose build pack. It builds the web and API containers,
runs Postgres with pgvector and private Ollama, and persists the database,
model weights, and ingested repositories in named volumes.

See [`docs/deploy-coolify.md`](docs/deploy-coolify.md) for VPS setup, Coolify
configuration, required environment variables, and domain routing. Ollama
inference runs on CPU unless the VPS is configured for GPU access; allow time
and disk space for the first model downloads.

## Environment

Copy `.env.example` to `.env` and fill in the values. `.env` is git-ignored and
must **never** be committed.

## Offline behavior

After dependencies and model weights are installed and a repository has been
ingested, the API, Postgres/pgvector retrieval, Gemma explanations, and the
GhostTrace CLI all run locally without a network connection. Importing a
repository from GitHub requires internet access; downloading Python/Node
dependencies and Ollama model weights also requires internet access unless
already cached. Optional Sentry delivery requires network access and a
configured DSN.

## Known limitations

- No user authentication or rate-limiting on the public Render deployment —
  treat it as a demo, not production infrastructure for untrusted traffic.
- GhostTrace's safety rules are pattern-based; they cover common
  destructive-command shapes (`rm -rf`, `git reset --hard`, `git push
  --force`, destructive SQL, etc.) but are not an exhaustive guarantee
  against every possible dangerous invocation.
- Evidence retrieval currently indexes commit messages, README content, and
  top-level file text — not full-repository semantic search over every file.
- CPU inference (the common case without a capable GPU) is noticeably
  slower than GPU — budget ~20+ seconds per Gemma call on CPU-only hardware.

---

AI coding assistance was used in building this project, across several
sessions and tools; see the project's DEV write-up for details.
