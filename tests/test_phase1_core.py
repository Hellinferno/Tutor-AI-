from __future__ import annotations

import base64
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "studylab_core"))

from studylab_core import StudyLabAPI  # noqa: E402
from studylab_core.retrieval import QdrantHybridSearchAdapter  # noqa: E402
from studylab_core.solver import normalize_question, question_hash  # noqa: E402
from studylab_core.text_processing import chunk_text  # noqa: E402


SAMPLE = """
Gradient descent updates parameters by moving opposite the gradient of the loss function.
The update rule is theta := theta - eta * gradient. Feature scaling helps convergence.
Net present value discounts each cash flow by the required return.
"""


class Phase1CoreTests(unittest.TestCase):
    def test_chunk_offsets_are_stable(self) -> None:
        chunks = chunk_text(SAMPLE, chunk_size=80, overlap=10)
        self.assertGreater(len(chunks), 1)
        for text, start, end in chunks:
            self.assertEqual(SAMPLE.strip()[start:end].strip(), text)

    def test_notebook_ask_uses_citations(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        upload = api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
        self.assertIn("gradient", upload["source_guide"]["key_concepts"])
        answer = api.ask_notebook(notebook["id"], "How does gradient descent update parameters?")
        self.assertEqual(answer["grounding"], "from_sources")
        self.assertGreaterEqual(len(answer["citations"]), 1)
        citation = answer["citations"][0]
        self.assertEqual(citation["source_title"], "Gradient Descent")
        self.assertIn("snippet", citation)

    def test_weak_retrieval_is_rejected(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
        answer = api.ask_notebook(notebook["id"], "Explain photosynthesis pigments")
        self.assertEqual(answer["grounding"], "insufficient_source_support")
        self.assertEqual(answer["citations"], [])

    def test_hybrid_retrieval_finds_exact_finance_formula_terms(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("Finance Notes")
        api.upload_source(
            notebook["id"],
            "Valuation",
            """
            Net present value, or NPV, discounts each cash flow by the required return.
            The formula is C0 + C1 / (1 + r) + C2 / (1 + r)^2.
            Gradient descent belongs to machine learning and is unrelated to valuation.
            """,
        )
        answer = api.ask_notebook(notebook["id"], "What is the NPV cash flow formula?")
        self.assertEqual(answer["grounding"], "from_sources")
        self.assertEqual(answer["citations"][0]["source_title"], "Valuation")
        self.assertIn("NPV", answer["citations"][0]["snippet"])

    def test_hybrid_retrieval_ranks_semantic_source_above_distractor(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("Mixed Notes")
        api.upload_source(
            notebook["id"],
            "Optimization",
            "Gradient descent changes parameters with a learning rate and a gradient direction.",
        )
        api.upload_source(
            notebook["id"],
            "Markets",
            "Bond markets price fixed income securities using yields, duration, and cash flows.",
        )
        answer = api.ask_notebook(notebook["id"], "How do parameters change during gradient learning?")
        self.assertEqual(answer["grounding"], "from_sources")
        self.assertEqual(answer["citations"][0]["source_title"], "Optimization")

    def test_qdrant_adapter_preserves_hybrid_contract_metadata(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        upload = api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
        source_id = upload["source"]["id"]
        chunk = next(chunk for chunk in api.store.chunks.values() if chunk.source_id == source_id)
        adapter = QdrantHybridSearchAdapter()
        point = adapter.point_payload(chunk, source_title="Gradient Descent")
        plan = adapter.query_plan(notebook["id"], "gradient update", top_k=5)
        self.assertEqual(point["payload"]["notebook_id"], notebook["id"])
        self.assertEqual(point["payload"]["source_id"], source_id)
        self.assertEqual(plan["collection"], "source_chunks")
        self.assertEqual(plan["rerank"]["limit"], 5)
        self.assertEqual(len(plan["prefetch"]), 2)

    def test_normalizer_hash_stability(self) -> None:
        self.assertEqual(normalize_question(" What is 2 + 2? "), "what is 2 + 2")
        self.assertEqual(question_hash("What is 2+2?"), question_hash("what is 2+2"))

    def test_symbolic_solver_verifies(self) -> None:
        api = StudyLabAPI()
        result = api.solve("What is 2 + 2 * 3?", subject="analytics")
        self.assertTrue(result["verified"])
        self.assertEqual(result["verify_method"], "symbolic")
        self.assertEqual(result["answer"], "8")

    def test_finance_solver_verifies_npv(self) -> None:
        api = StudyLabAPI()
        result = api.solve("Calculate NPV at 10% for cash flows -100, 60, 60.", subject="finance")
        self.assertTrue(result["verified"])
        self.assertEqual(result["verify_method"], "formula")
        self.assertEqual(result["answer"], "4.13")

    def test_reveal_uses_stored_solution(self) -> None:
        api = StudyLabAPI()
        result = api.solve("What is 2 + 2?", subject="analytics")
        step = api.reveal(result["solution_id"], 1)
        self.assertTrue(step["revealed"])
        cached = api.solve("What is 2 + 2?", subject="analytics")
        self.assertTrue(cached["from_cache"])

    def test_artifact_and_notion_mock_export(self) -> None:
        api = StudyLabAPI()
        notebook = api.create_notebook("ML Notes")
        api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
        artifact = api.generate_artifact(notebook["id"], "summary_notes")
        self.assertIn("Summary Notes", artifact["title"])
        export = api.export_to_notion(artifact["id"], mock=True)
        self.assertTrue(export["connected"])
        self.assertIn("notion.local", export["page_url"])

    def test_ocr_image_payload_enters_solver(self) -> None:
        api = StudyLabAPI()
        payload = base64.b64encode(b"What is 3 + 4?").decode("utf-8")
        result = api.solve(payload, input_type="image", subject="analytics")
        self.assertTrue(result["verified"])
        self.assertEqual(result["answer"], "7")


if __name__ == "__main__":
    unittest.main()
