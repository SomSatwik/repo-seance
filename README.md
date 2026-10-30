# Repo Séance 👻

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
- (Optional) NVIDIA GPU + Ollama for local inference

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

### 3. Web

```powershell
cd apps/web
pnpm install
pnpm dev
```

Open http://localhost:3000 — the homepage fetches the API `/health` endpoint live.

## Environment

Copy `.env.example` to `.env` and fill in the values. `.env` is git-ignored and
must **never** be committed.
