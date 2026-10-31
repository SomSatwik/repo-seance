# Architecture

## Overview

```
┌────────────────────────┐          ┌────────────────────────┐
│  apps/web (Next.js)    │  /health │  apps/api (FastAPI)    │
│  http://localhost:3000 │ ───────▶ │  http://localhost:8000 │
└────────────────────────┘          └───────────┬────────────┘
                                                │ SQLAlchemy
                                                ▼
                                     ┌────────────────────────┐
                                     │  Postgres 15 + pgvector │
                                     │  localhost:5434         │
                                     └────────────────────────┘
                                                ▲
                                     ┌────────────────────────┐
                                     │  Ollama (native Win)    │
                                     │  localhost:11434        │
                                     │  embeddings + LLM       │
                                     └────────────────────────┘
```

For the cloud deployment, `render.yaml` provisions the same components in
Singapore: a public Next.js service, a public FastAPI service, Render Postgres
with pgvector, and private CPU Ollama. The API's local Git clones and Ollama's
model cache are mounted on separate persistent disks.

For single-server self-hosting, `infra/docker-compose.coolify.yml` builds the
Next.js and FastAPI applications alongside Postgres/pgvector and Ollama.
Coolify routes public domains to the web and API containers; the database and
model service remain internal to the Compose network.

## Components

- **apps/web** — Next.js (TypeScript, Tailwind, App Router). User-facing UI.
- **apps/api** — FastAPI service. Git ingestion, embedding pipeline, and query API.
- **infra** — Docker Compose for Postgres + pgvector.
- **Ollama** — runs natively on Windows (not containerized) for GPU acceleration.

## Decisions Log

| Date       | Decision                                              | Rationale                                                              |
| ---------- | ----------------------------------------------------- | ---------------------------------------------------------------------- |
| 2026-10-30 | Postgres pinned to host port **5434**                 | Avoid collision with existing dev containers (postgres 5433, redis 6380). |
| 2026-10-30 | pgvector via the `pgvector/pgvector:pg15` image       | Official image bundles the `vector` extension; no manual compile step. |
| 2026-10-30 | Ollama runs natively on Windows (not containerized)   | Best GPU performance on the RTX 4050 vs. containerized CPU inference.  |
| 2026-10-30 | Published to GitHub (public)                          | <https://github.com/SomSatwik/repo-seance> — hackathon submission, judgeable. |
