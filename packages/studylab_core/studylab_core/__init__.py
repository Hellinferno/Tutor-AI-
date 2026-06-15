from .analytics import AnalyticsEngine
from .api import StudyLabAPI
from .artifacts import ArtifactGenerator
from .auth import AuthEngine, AuthError, hash_password, verify_password
from .classrooms import ClassroomEngine
from .connectors import SourceConnectorEngine
from .eval import EvalEngine
from .metrics import MetricsCollector
from .notion import NotionExporter
from .paper import PaperEngine
from .pricing import (
    PLAN_CATALOG,
    BillingProvider,
    MockBillingProvider,
    PricingEngine,
    QuotaExceededError,
    StripeBillingProvider,
    make_billing_provider,
)
from .quiz import QuizEngine
from .rag import RagEngine
from .ratelimit import RateLimiter, RateLimitError, make_rate_limiter_from_env
from .retrieval import (
    EmbeddingProvider,
    HttpEmbeddingProvider,
    HybridRetriever,
    LocalHashEmbeddingProvider,
    OpenAIEmbeddingProvider,
    QdrantHybridSearchAdapter,
    make_embedding_provider,
    make_qdrant_adapter,
)
from .revision import RepetitionEngine
from .social import SocialEngine
from .solver import SolverEngine
from .store import InMemoryStudyLabStore
from .store_sqlite import SqliteStudyLabStore, make_store_from_env
from .student import StudentModel
from .teaching import TeachingEngine
from .voice import GeminiVoiceProvider, MockVoiceProvider, VoiceProvider, make_voice_provider

__all__ = [
    "AnalyticsEngine",
    "ArtifactGenerator",
    "AuthEngine",
    "AuthError",
    "BillingProvider",
    "ClassroomEngine",
    "EmbeddingProvider",
    "EvalEngine",
    "GeminiVoiceProvider",
    "hash_password",
    "HttpEmbeddingProvider",
    "HybridRetriever",
    "InMemoryStudyLabStore",
    "LocalHashEmbeddingProvider",
    "make_billing_provider",
    "make_embedding_provider",
    "make_qdrant_adapter",
    "make_store_from_env",
    "make_voice_provider",
    "OpenAIEmbeddingProvider",
    "MetricsCollector",
    "MockBillingProvider",
    "MockVoiceProvider",
    "NotionExporter",
    "PaperEngine",
    "PLAN_CATALOG",
    "PricingEngine",
    "make_rate_limiter_from_env",
    "QdrantHybridSearchAdapter",
    "QuizEngine",
    "QuotaExceededError",
    "RagEngine",
    "RateLimiter",
    "RateLimitError",
    "RepetitionEngine",
    "SocialEngine",
    "SolverEngine",
    "SourceConnectorEngine",
    "SqliteStudyLabStore",
    "StripeBillingProvider",
    # Phase 10 — Postgres store is re-exported lazily via the module path
    # ``studylab_core.store_postgres``. We don't import it eagerly here so the
    # package still imports cleanly without psycopg installed.
    "StudentModel",
    "StudyLabAPI",
    "TeachingEngine",
    "verify_password",
    "VoiceProvider",
]
