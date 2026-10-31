"""Application settings (env-configurable)."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# repo-seance/ (two levels up from apps/api/config.py)
REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5434/reposeance"
    data_dir: Path = REPO_ROOT / "data"
    cors_origins: str = "*"

    # Ingestion limits (override via env, e.g. CLONE_TIMEOUT_SECONDS=60)
    clone_timeout_seconds: int = 120
    clone_max_size_mb: int = 500
    clone_depth: int = 0
    max_files: int = 5000
    max_tree_depth: int = 6

    # Ollama (local LLM + embeddings)
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "gemma2:2b"
    ollama_embed_model: str = "nomic-embed-text"
    sentry_dsn: str | None = None

    # GhostTrace terminal companion (opt-in, project-scoped)
    ghosttrace_enabled: bool = False
    ghosttrace_project_scope_only: bool = True

    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
