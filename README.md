# Repo Séance

```
  .-.
 ( o o )
  | O |
```

**Repository:** <https://github.com/SomSatwik/repo-seance>

> **Repo Séance** — summon the spirit of any git repository. A local, AI-powered
> forensic analyzer that ingests a codebase's full git history and lets you
> interrogate its ghosts in natural language.

Repo Séance reconstructs the "soul" of a repository — its commits, branches, and
the stories embedded in its source — and makes it searchable through a semantic,
vector-backed memory. Point it at any git repo and it will index the history,
embed it locally, and answer questions like *"who touched this function last and
why?"* or *"what changed around the v2.0 release?"*.

## Architecture

| Component      | Stack                                        | Port  |
| -------------- | -------------------------------------------- | ----- |
| Web UI         | Next.js (TypeScript, Tailwind, App Router)    | 3000  |
| API            | FastAPI (Python 3.12)                        | 8000  |
| Database       | Postgres 15 + pgvector (Docker)              | 5434  |
| Embeddings/LLM | Ollama (native Windows, GPU)                 | 11434 |

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

### GhostTrace (opt-in)

Set `GHOSTTRACE_ENABLED=true` in the root `.env` to enable the project-scoped
GhostTrace endpoint. Keep `GHOSTTRACE_PROJECT_SCOPE_ONLY=true` to limit
retrieved context to the selected repository. Install the CLI from the repo
root with `pip install -e packages/ghosttrace-cli`, then run
`ghosttrace --repo <repo-id>` while the API is running.

### Optional Sentry

Set `SENTRY_DSN` in the root `.env` to enable API error reporting and Ollama
generation spans. No DSN is required for local development; Sentry is disabled
when the setting is empty. Prompts and local variables are not sent as Sentry
event data.

## Environment

Copy `.env.example` to `.env` and fill in the values. `.env` is git-ignored and
must **never** be committed.

## Offline behavior

After dependencies and model weights are installed and a repository has been
ingested, the API, Postgres/pgvector retrieval, and Gemma explanations run
locally without a network connection. Importing a repository from GitHub
requires internet access; downloading Python/Node dependencies and Ollama model
weights also requires internet access unless already cached. Optional Sentry
delivery requires network access and a configured DSN.
