# settings loaded from env vars
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/groundedqa"
    OPENAI_API_KEY: str = ""
    # Embedding provider. Defaults point at OpenAI. Override EMBEDDING_BASE_URL,
    # EMBEDDING_MODEL, EMBEDDING_DIM, and EMBEDDING_API_KEY via env vars to use
    # another OpenAI-compatible endpoint. EMBEDDING_API_KEY falls back to
    # OPENAI_API_KEY when empty.
    EMBEDDING_BASE_URL: str = "https://api.openai.com/v1"
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    # Chat provider. Defaults point at OpenAI. Override CHAT_BASE_URL, CHAT_MODEL,
    # and CHAT_API_KEY via env vars. CHAT_API_KEY falls back to OPENAI_API_KEY
    # when empty.
    CHAT_BASE_URL: str = "https://api.openai.com/v1"
    CHAT_API_KEY: str = ""
    CHAT_MODEL: str = "gpt-4o-mini"
    EMBEDDING_DIM: int = 1536
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    TOP_K: int = 5
    SIMILARITY_CUTOFF: float = 0.3
    MAX_UPLOAD_MB: int = 10
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
