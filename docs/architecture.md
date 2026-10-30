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
