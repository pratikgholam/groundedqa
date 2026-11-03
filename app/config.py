# settings loaded from env vars
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/groundedqa"
    OPENAI_API_KEY: str = ""
    # Embedding provider. Defaults point at a local Ollama server
    # (OpenAI-compatible /v1/embeddings endpoint). To use OpenAI or another
    # provider, override EMBEDDING_BASE_URL, EMBEDDING_MODEL, EMBEDDING_DIM,
    # and EMBEDDING_API_KEY via env vars.
    EMBEDDING_BASE_URL: str = "http://localhost:11434/v1"
    EMBEDDING_API_KEY: str = "ollama"  # Ollama ignores it; the SDK needs a non-empty key
    EMBEDDING_MODEL: str = "nomic-embed-text"
    # Chat provider. Defaults point at a local Ollama server
    # (OpenAI-compatible /v1/chat/completions endpoint). To use OpenAI or another
    # provider, override CHAT_BASE_URL, CHAT_MODEL, and CHAT_API_KEY via env vars.
    CHAT_BASE_URL: str = "http://localhost:11434/v1"
    CHAT_API_KEY: str = "ollama"  # Ollama ignores it; the SDK needs a non-empty key
    CHAT_MODEL: str = "lfm3-qa:latest"
    EMBEDDING_DIM: int = 768
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    TOP_K: int = 5
    SIMILARITY_CUTOFF: float = 0.3
    MAX_UPLOAD_MB: int = 10
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
