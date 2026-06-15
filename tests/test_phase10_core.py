"""Phase 10 tests: production embedding providers, live Qdrant adapter, Postgres store,
admin storage diagnostics.

These exercise the *contract* of the new env-gated paths without requiring the live
external services to be reachable. Tests that need a real Postgres or Qdrant cluster
skip cleanly when the driver / env var isn't available, so the suite still passes on
a vanilla machine.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from http.client import HTTPResponse
from io import BytesIO
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "studylab_core"))

from studylab_core import StudyLabAPI  # noqa: E402
from studylab_core.retrieval import (  # noqa: E402
    HttpEmbeddingProvider,
    HybridRetriever,
    LocalHashEmbeddingProvider,
    OpenAIEmbeddingProvider,
    QdrantHybridSearchAdapter,
    make_embedding_provider,
    make_qdrant_adapter,
)

SAMPLE = (
    "Gradient descent moves opposite the gradient of the loss. "
    "Theta := theta - eta * gradient. The learning rate controls step size."
)


class _EnvGuard:
    def __init__(self, **values: str | None) -> None:
        self.values = values
        self._saved: dict[str, str | None] = {}

    def __enter__(self):
        for k, v in self.values.items():
            self._saved[k] = os.environ.get(k)
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        return self

    def __exit__(self, *exc):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _fake_urlopen(payload: dict, *, status: int = 200):
    """Return a context manager that mimics urllib.request.urlopen."""

    class _Resp:
        def __init__(self):
            self._body = json.dumps(payload).encode("utf-8")

        def read(self):
            return self._body

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    return lambda *a, **kw: _Resp()


# ── Embedding provider factory ─────────────────────────────────────────────

class Phase10EmbeddingFactoryTests(unittest.TestCase):
    def test_default_is_local_hash(self) -> None:
        with _EnvGuard(EMBEDDINGS_PROVIDER=None, OPENAI_API_KEY=None, EMBEDDINGS_ENDPOINT=None):
            provider = make_embedding_provider()
        self.assertIsInstance(provider, LocalHashEmbeddingProvider)
        self.assertEqual(provider.name, "local_hash")
        vector = provider.embed("gradient descent")
        self.assertEqual(len(vector), provider.dimensions)
        # Should be unit-normalized.
        magnitude = sum(v * v for v in vector) ** 0.5
        self.assertAlmostEqual(magnitude, 1.0, places=4)

    def test_explicit_local_wins(self) -> None:
        with _EnvGuard(EMBEDDINGS_PROVIDER="local", OPENAI_API_KEY="sk-test"):
            provider = make_embedding_provider()
        self.assertIsInstance(provider, LocalHashEmbeddingProvider)

    def test_openai_chosen_when_key_present(self) -> None:
        with _EnvGuard(EMBEDDINGS_PROVIDER=None, OPENAI_API_KEY="sk-test", EMBEDDINGS_ENDPOINT=None):
            provider = make_embedding_provider()
        self.assertIsInstance(provider, OpenAIEmbeddingProvider)
        self.assertEqual(provider.name, "openai")
        self.assertEqual(provider.api_key, "sk-test")

    def test_http_chosen_when_endpoint_present(self) -> None:
        with _EnvGuard(EMBEDDINGS_PROVIDER=None, OPENAI_API_KEY=None, EMBEDDINGS_ENDPOINT="http://emb.local/embed"):
            provider = make_embedding_provider()
        self.assertIsInstance(provider, HttpEmbeddingProvider)
        self.assertEqual(provider.name, "http")
        self.assertEqual(provider.endpoint, "http://emb.local/embed")

    def test_real_provider_failure_falls_back_to_local(self) -> None:
        # OPENAI_API_KEY set but constructor raises -> shouldn't propagate.
        with mock.patch("studylab_core.retrieval.OpenAIEmbeddingProvider", side_effect=RuntimeError("kaboom")):
            with _EnvGuard(OPENAI_API_KEY="sk-test", EMBEDDINGS_ENDPOINT=None, EMBEDDINGS_PROVIDER=None):
                provider = make_embedding_provider()
        self.assertIsInstance(provider, LocalHashEmbeddingProvider)


# ── Real-provider HTTP wiring (with mocked transport) ──────────────────────

class Phase10HttpProviderTests(unittest.TestCase):
    def test_http_provider_posts_input_and_normalizes(self) -> None:
        with _EnvGuard(EMBEDDINGS_ENDPOINT="http://emb.local/embed", EMBEDDINGS_API_KEY="k-test"):
            provider = HttpEmbeddingProvider()
        with mock.patch(
            "studylab_core.retrieval.urllib.request.urlopen",
            _fake_urlopen({"embedding": [3.0, 4.0]}),
        ):
            vector = provider.embed("gradient descent")
        # 3/5, 4/5 after normalization
        self.assertAlmostEqual(vector[0], 0.6, places=4)
        self.assertAlmostEqual(vector[1], 0.8, places=4)

    def test_openai_provider_posts_to_embeddings_endpoint(self) -> None:
        with _EnvGuard(OPENAI_API_KEY="sk-test"):
            provider = OpenAIEmbeddingProvider()
        with mock.patch(
            "studylab_core.retrieval.urllib.request.urlopen",
            _fake_urlopen({"data": [{"embedding": [0.0, 1.0]}]}),
        ):
            vector = provider.embed("gradient descent")
        self.assertEqual(vector, [0.0, 1.0])  # already unit length

    def test_openai_raises_when_no_key(self) -> None:
        with _EnvGuard(OPENAI_API_KEY=None):
            with self.assertRaises(RuntimeError):
                OpenAIEmbeddingProvider()


# ── Qdrant adapter ────────────────────────────────────────────────────────

class Phase10QdrantAdapterTests(unittest.TestCase):
    def test_default_adapter_is_not_live(self) -> None:
        with _EnvGuard(QDRANT_URL=None):
            adapter = QdrantHybridSearchAdapter()
        self.assertFalse(adapter.is_live())
        self.assertEqual(adapter.search_vector_ids("nb", "q", [0.1, 0.2]), [])

    def test_make_qdrant_adapter_returns_none_without_url(self) -> None:
        with _EnvGuard(QDRANT_URL=None):
            self.assertIsNone(make_qdrant_adapter())

    def test_make_qdrant_adapter_returns_live_when_configured(self) -> None:
        with _EnvGuard(QDRANT_URL="http://qdrant.local:6333", QDRANT_COLLECTION="nb_chunks"):
            adapter = make_qdrant_adapter()
        self.assertIsNotNone(adapter)
        self.assertTrue(adapter.is_live())
        self.assertEqual(adapter.collection, "nb_chunks")

    def test_search_vector_ids_parses_hits(self) -> None:
        with _EnvGuard(QDRANT_URL="http://qdrant.local:6333"):
            adapter = QdrantHybridSearchAdapter()
        with mock.patch(
            "studylab_core.retrieval.urllib.request.urlopen",
            _fake_urlopen({"result": [{"id": "v1"}, {"id": "v2"}]}),
        ):
            ids = adapter.search_vector_ids("nb-1", "loss", [0.1, 0.2])
        self.assertEqual(ids, ["v1", "v2"])

    def test_retriever_restricts_candidates_to_qdrant_hits(self) -> None:
        api = StudyLabAPI()
        nb = api.create_notebook("ml")
        api.upload_source(nb["id"], "Notes", SAMPLE)
        all_chunks = api.store.notebook_chunks(nb["id"])
        # Fake Qdrant returns only one chunk vector_id.
        wanted = all_chunks[0].vector_id

        adapter = QdrantHybridSearchAdapter(url="http://qdrant.local:6333")
        with mock.patch.object(adapter, "search_vector_ids", return_value=[wanted]):
            retriever = HybridRetriever(api.store, qdrant=adapter)
            citations = retriever.retrieve(notebook_id=nb["id"], query="gradient descent")
        # Should still return citations, drawn only from the Qdrant-allowed set.
        self.assertGreater(len(citations), 0)
        wanted_chunk = next(c for c in all_chunks if c.vector_id == wanted)
        for citation in citations:
            self.assertEqual(citation.chunk_index, wanted_chunk.chunk_index)

    def test_retriever_falls_back_when_qdrant_throws(self) -> None:
        api = StudyLabAPI()
        nb = api.create_notebook("ml")
        api.upload_source(nb["id"], "Notes", SAMPLE)

        adapter = QdrantHybridSearchAdapter(url="http://qdrant.local:6333")
        with mock.patch.object(adapter, "search_vector_ids", side_effect=RuntimeError("boom")):
            retriever = HybridRetriever(api.store, qdrant=adapter)
            citations = retriever.retrieve(notebook_id=nb["id"], query="gradient descent")
        # Without Qdrant we'd still get hits from local recall — never silently empty.
        self.assertGreater(len(citations), 0)


# ── Postgres store ─────────────────────────────────────────────────────────

class Phase10PostgresStoreTests(unittest.TestCase):
    def test_postgres_module_imports_without_psycopg(self) -> None:
        # Importing the module is always safe; the driver is only required at
        # instantiation time.
        from studylab_core import store_postgres  # noqa: F401

    def test_instantiation_raises_clear_error_when_driver_missing(self) -> None:
        from studylab_core.store_postgres import PostgresStudyLabStore

        # Force-load failure even if psycopg is installed.
        with mock.patch("studylab_core.store_postgres._load_psycopg", side_effect=RuntimeError("driver missing")):
            with self.assertRaises(RuntimeError):
                PostgresStudyLabStore()

    def test_make_store_falls_back_to_sqlite_when_pg_unavailable(self) -> None:
        from studylab_core.store_sqlite import make_store_from_env

        # DATABASE_URL set but psycopg unavailable -> falls through to SQLite, not crash.
        tmp = ROOT / "data" / "phase10_fallback.db"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        with _EnvGuard(
            DATABASE_URL="postgres://invalid",
            STUDYLAB_POSTGRES_URL=None,
            STUDYLAB_SQLITE_PATH=str(tmp),
        ):
            store = make_store_from_env()
        self.assertEqual(type(store).__name__, "SqliteStudyLabStore")
        store.close()

    @unittest.skipUnless(
        os.getenv("STUDYLAB_TEST_POSTGRES_URL"),
        "STUDYLAB_TEST_POSTGRES_URL not set — skipping live Postgres roundtrip.",
    )
    def test_live_roundtrip(self) -> None:  # pragma: no cover - requires live DB
        from studylab_core.store_postgres import PostgresStudyLabStore

        store = PostgresStudyLabStore(dsn=os.environ["STUDYLAB_TEST_POSTGRES_URL"])
        api = StudyLabAPI(store)
        owner = api.register_user("phase10@x.com", "password1")["user"]
        nb = api.create_notebook("Live", user_id=owner["id"])
        api.upload_source(nb["id"], "Notes", SAMPLE)
        chunks = api.store.notebook_chunks(nb["id"])
        self.assertGreater(len(chunks), 0)
        store.close()


# ── Storage diagnostics endpoint ────────────────────────────────────────────

class Phase10DiagnosticsTests(unittest.TestCase):
    def test_diagnostics_admin_only(self) -> None:
        api = StudyLabAPI()
        student = api.register_user("kid@x.com", "password1")["user"]
        with self.assertRaises(PermissionError):
            api.storage_diagnostics(student["id"])

    def test_diagnostics_shape_for_default_offline_setup(self) -> None:
        with _EnvGuard(STUDYLAB_ADMIN_EMAILS="boss@x.com", OPENAI_API_KEY=None, EMBEDDINGS_ENDPOINT=None, QDRANT_URL=None):
            api = StudyLabAPI()
            boss = api.register_user("boss@x.com", "password1")["user"]
            snapshot = api.storage_diagnostics(boss["id"])
        self.assertEqual(snapshot["store"]["backend"], "InMemoryStudyLabStore")
        self.assertFalse(snapshot["store"]["durable"])
        self.assertFalse(snapshot["store"]["production_backend"])
        self.assertFalse(snapshot["qdrant"]["configured"])
        self.assertEqual(snapshot["embeddings"]["provider"], "local_hash")

    def test_diagnostics_reflects_qdrant_when_configured(self) -> None:
        with _EnvGuard(
            STUDYLAB_ADMIN_EMAILS="boss@x.com",
            QDRANT_URL="http://qdrant.local:6333",
            QDRANT_COLLECTION="src",
        ):
            api = StudyLabAPI()
            boss = api.register_user("boss@x.com", "password1")["user"]
            snapshot = api.storage_diagnostics(boss["id"])
        self.assertTrue(snapshot["qdrant"]["configured"])
        self.assertEqual(snapshot["qdrant"]["collection"], "src")


if __name__ == "__main__":
    unittest.main()
