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


class QueryTransformSettings(BaseSettings):
    """Feature flags and limits for query transformation pipeline."""

    model_config = SettingsConfigDict(env_prefix="QT_")
    enable_rewrite: bool = False
    enable_acronym_expansion: bool = False
    enable_hyde: bool = False
    enable_decomposition: bool = False
    # Latency budget per transform in milliseconds (0 = no limit)
    rewrite_timeout_ms: int = 3000
    hyde_timeout_ms: int = 5000
    decomposition_timeout_ms: int = 5000
    # Decomposition settings
    max_sub_queries: int = 3
    # Domain dictionary (JSON string or file path)
    acronym_dict: dict[str, str] = {}


class HybridRetrievalSettings(BaseSettings):
    """Controls for hybrid (dense + lexical) retrieval and reranking."""

    model_config = SettingsConfigDict(env_prefix="HYBRID_")
    enable_lexical: bool = False
    enable_reranking: bool = False
    dense_weight: float = 1.0  # RRF weight for dense results
    lexical_weight: float = 1.0  # RRF weight for lexical results
    dense_top_k: int = 20  # candidates from dense search
    lexical_top_k: int = 20  # candidates from lexical search
    rrf_k: int = 60  # RRF constant (higher = less emphasis on top ranks)
    rerank_top_n: int = 20  # how many RRF results to rerank
    final_context_k: int = 5  # final chunks returned to caller
    reranker_type: str = "cross_encoder"  # cross_encoder | late_interaction
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranker_timeout_ms: int = 10000


class AnswerGenerationSettings(BaseSettings):
    """Controls for the answer generation (RAG) layer."""

    model_config = SettingsConfigDict(env_prefix="ANSWER_")
    default_mode: str = "standard"  # concise | standard | detailed
    temperature: float = 0.1
    max_tokens_concise: int = 256
    max_tokens_standard: int = 1024
    max_tokens_detailed: int = 4096
    timeout_ms: int = 30000


class AuthSettings(BaseSettings):
    """Authentication and authorization configuration.

    AUTH_BACKEND controls the authentication strategy:
        - "none"    → trust x-tenant-id / x-user-id headers (dev/testing)
        - "api_key" → validate x-api-key against per-tenant keys
        - "jwt"     → validate Bearer token (future: OIDC / external IdP)

    AUTH_REQUIRE_USER_ID → 403 if x-user-id header missing (audit enforcement).
    """

    model_config = SettingsConfigDict(env_prefix="AUTH_")
    backend: str = "none"  # none | api_key | jwt
    require_user_id: bool = False
    # API-key backend
    api_key_header: str = "x-api-key"
    # JWT backend (future)
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_audience: str = ""


class GuardrailSettings(BaseSettings):
    """Controls for the guardrail / content-safety layer.

    GUARD_ prefix for all env vars.
    """

    model_config = SettingsConfigDict(env_prefix="GUARD_")
    # Master switch
    enabled: bool = True
    # Ingestion sanitization
    sanitize_on_ingest: bool = True
    reject_on_hidden_text: bool = True
    max_hidden_text_ratio: float = 0.1        # reject if >10% hidden
    # Prompt injection detection
    detect_prompt_injection: bool = True
    injection_score_threshold: float = 0.7    # 0.0-1.0; above → block
    # Source trust
    classify_source_trust: bool = True
    default_trust_level: str = "untrusted"    # trusted | untrusted
    trusted_source_types: list[str] = ["upload"]
    # PII redaction
    redact_pii: bool = True
    pii_patterns: list[str] = [
        "email", "phone", "ssn", "credit_card", "ip_address",
    ]
    pii_action: str = "redact"  # redact | flag | block
    # Output validation
    validate_output: bool = True
    max_output_length: int = 50000
    block_output_injection: bool = True
    # Human review
    human_review_enabled: bool = True
    human_review_severity_threshold: str = "high"  # low|medium|high|critical


class RAGOpsSettings(BaseSettings):
    """Controls for the RAGOps observability and evaluation layer."""

    model_config = SettingsConfigDict(env_prefix="RAGOPS_")
    # Tracing
    tracing_enabled: bool = True
    trace_spans_to_metadata: bool = True  # write spans to trace JSONB
    # Evaluation
    eval_judge_model: str = "gpt-4o-mini"
    eval_judge_temperature: float = 0.0
    eval_judge_max_tokens: int = 512
    eval_timeout_ms: int = 30000
    # Thresholds (scores below these fail in CI)
    min_context_relevance: float = 0.5
    min_groundedness: float = 0.5
    min_answer_relevance: float = 0.5


class GraphRAGSettings(BaseSettings):
    """Controls for the optional GraphRAG extension.

    GRAPH_ prefix for all env vars. Disabled by default so the
    existing vector pipeline runs unmodified.
    """

    model_config = SettingsConfigDict(env_prefix="GRAPH_")
    # Master toggle
    enabled: bool = False
    # Graph store backend
    store_backend: str = "postgres"  # postgres | neo4j
    # Neo4j connection (only used when store_backend == "neo4j")
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"
    # Entity extraction
    extraction_model: str = "gpt-4o-mini"
    extraction_temperature: float = 0.0
    extraction_max_tokens: int = 2048
    max_entities_per_chunk: int = 20
    max_relationships_per_chunk: int = 30
    # Community detection
    community_algorithm: str = "leiden"  # leiden | louvain
    community_resolution: float = 1.0
    min_community_size: int = 3
    max_community_summary_tokens: int = 512
    # Retrieval
    local_search_hops: int = 2            # neighbourhood depth
    local_max_entities: int = 20          # max entities returned
    global_max_communities: int = 10      # top-N communities for summaries
    entity_score_threshold: float = 0.3   # min similarity for entity match
    # Routing
    auto_route: bool = True  # auto-decide vector vs graph vs hybrid


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AGENT_")

    enabled: bool = False
    max_iterations: int = 6
    max_tokens: int = 32_000
    max_tool_calls: int = 10
    max_evidence_items: int = 20
    reflection_threshold: float = 0.7
    planning_temperature: float = 0.2
    answer_temperature: float = 0.1
    enable_web_tool: bool = False
    enable_python_tool: bool = False
    auto_route: bool = True  # auto-decide simple vs agentic


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
    query_transform: QueryTransformSettings = QueryTransformSettings()
    hybrid_retrieval: HybridRetrievalSettings = HybridRetrievalSettings()
    answer_generation: AnswerGenerationSettings = AnswerGenerationSettings()
    auth: AuthSettings = AuthSettings()
    guardrails: GuardrailSettings = GuardrailSettings()
    ragops: RAGOpsSettings = RAGOpsSettings()
    graph_rag: GraphRAGSettings = GraphRAGSettings()
    agent: AgentSettings = AgentSettings()


@lru_cache
def get_settings() -> Settings:
    return Settings()
