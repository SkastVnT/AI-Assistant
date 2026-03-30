"""Centralized settings via pydantic-settings. Reads from .env automatically."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class PostgresSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="POSTGRES_")
    host: str = "localhost"
    port: int = 5432
    db: str = "rag"
    user: str = "rag_user"
    password: str = "change_me_in_production"

    @property
    def dsn(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

    @property
    def sync_dsn(self) -> str:
        return f"postgresql+psycopg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REDIS_")
    host: str = "localhost"
    port: int = 6379
    password: str = ""

    @property
    def url(self) -> str:
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/0"


class MinIOSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MINIO_")
    endpoint: str = "localhost:9000"
    access_key: str = "minioadmin"
    secret_key: str = "minioadmin"
    bucket: str = "rag-documents"
    use_ssl: bool = False


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LLM_")
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    api_key: str = ""


class EmbeddingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EMBEDDING_")
    provider: str = "openai"
    model: str = "text-embedding-3-small"
    api_key: str = ""
    dimensions: int = 1536
    batch_size: int = 100
    max_retries: int = 3
    version: str = "v1"


class ChunkingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CHUNK_")
    size: int = 512
    overlap: int = 64


class APISettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="API_")
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    log_level: str = "info"


class IngestionSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="INGESTION_")
    max_retries: int = 3
    poll_interval: int = 5
    batch_size: int = 5


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    postgres: PostgresSettings = PostgresSettings()
    redis: RedisSettings = RedisSettings()
    minio: MinIOSettings = MinIOSettings()
    llm: LLMSettings = LLMSettings()
    embedding: EmbeddingSettings = EmbeddingSettings()
    chunking: ChunkingSettings = ChunkingSettings()
    api: APISettings = APISettings()
    ingestion: IngestionSettings = IngestionSettings()


@lru_cache
def get_settings() -> Settings:
    return Settings()
