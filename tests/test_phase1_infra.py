from __future__ import annotations

import base64
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "studylab_core"))

from studylab_core import StudyLabAPI, SqliteStudyLabStore  # noqa: E402
from studylab_core.prompts import list_prompts, load_prompt, render_prompt  # noqa: E402
from studylab_core.sandbox import extract_code, run_code, validate_code  # noqa: E402
from studylab_core.service_http import Route  # noqa: E402


SAMPLE = (
    "Gradient descent updates parameters by moving opposite the gradient of the loss. "
    "The update rule is theta := theta - eta * gradient."
)


class SqlitePersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.mkdtemp()
        self.path = str(Path(self.dir) / "studylab.db")

    def test_data_survives_reopen(self) -> None:
        api = StudyLabAPI(SqliteStudyLabStore(self.path))
        notebook = api.create_notebook("ML Notes")
        upload = api.upload_source(notebook["id"], "Gradient Descent", SAMPLE)
        source_id = upload["source"]["id"]
        artifact = api.generate_artifact(notebook["id"], "summary_notes")
        solution = api.solve("What is 2 + 2 * 3?", subject="analytics")
        api.store.close()

        reopened = StudyLabAPI(SqliteStudyLabStore(self.path))
        answer = reopened.ask_notebook(notebook["id"], "How does gradient descent update parameters?")
        self.assertEqual(answer["grounding"], "from_sources")
        self.assertGreaterEqual(len(answer["citations"]), 1)
        self.assertIn("gradient", reopened.get_source(source_id)["source_guide"]["key_concepts"])
        self.assertIn(artifact["id"], reopened.store.artifacts)
        cached = reopened.solve("What is 2 + 2 * 3?", subject="analytics")
        self.assertTrue(cached["from_cache"])
        self.assertEqual(cached["answer"], "8")
        reopened.store.close()

    def test_reveal_persists_across_reopen(self) -> None:
        api = StudyLabAPI(SqliteStudyLabStore(self.path))
        solution = api.solve("What is 2 + 2?", subject="analytics")
        api.reveal(solution["solution_id"], 1)
        api.store.close()

        reopened = StudyLabAPI(SqliteStudyLabStore(self.path))
        stored = reopened.store.require_solution(solution["solution_id"])
        revealed = {step["idx"]: step["revealed"] for step in stored.steps}
        self.assertTrue(revealed[1])
        reopened.store.close()


class SandboxTests(unittest.TestCase):
    def test_code_exec_is_verified(self) -> None:
        api = StudyLabAPI()
        result = api.solve("```python\nprint(6 * 7)\n```", subject="analytics")
        self.assertTrue(result["verified"])
        self.assertEqual(result["verify_method"], "code_exec")
        self.assertEqual(result["answer"], "42")

    def test_disallowed_import_is_rejected(self) -> None:
        result = StudyLabAPI().solve(
            "```python\nimport socket\nprint(socket.gethostname())\n```", subject="analytics"
        )
        self.assertFalse(result["verified"])
        self.assertEqual(result["verify_method"], "unverified")
        self.assertIn("socket", result["answer"])

    def test_validate_blocks_dangerous_builtins(self) -> None:
        self.assertIsNotNone(validate_code("open('/etc/passwd')"))
        self.assertIsNotNone(validate_code("__import__('os').system('echo hi')"))
        self.assertIsNone(validate_code("import math\nprint(math.pi)"))

    def test_extract_code_prefers_fenced_block(self) -> None:
        self.assertEqual(extract_code("```python\nprint(1)\n```"), "print(1)")
        self.assertIsNone(extract_code("Explain gradient descent in words."))

    def test_run_code_captures_stdout(self) -> None:
        verdict = run_code("print(2 ** 5)")
        self.assertTrue(verdict.ok)
        self.assertEqual(verdict.output, "32")


class PromptTests(unittest.TestCase):
    def test_all_registered_prompts_load(self) -> None:
        names = list_prompts()
        self.assertIn("solver_system", names)
        for name in names:
            self.assertTrue(load_prompt(name).strip())

    def test_unknown_prompt_raises(self) -> None:
        with self.assertRaises(KeyError):
            load_prompt("does_not_exist")

    def test_render_substitutes_placeholders(self) -> None:
        rendered = render_prompt("notebook_answer", query="What is NPV?", chunks="(none)")
        self.assertIn("What is NPV?", rendered)
        self.assertNotIn("{{query}}", rendered)


class ServiceRouterTests(unittest.TestCase):
    def test_route_matches_and_extracts_params(self) -> None:
        route = Route("POST", "/v1/notebooks/{notebook_id}/ask", lambda p, b: p)
        self.assertEqual(route.match("POST", ["v1", "notebooks", "abc", "ask"]), {"notebook_id": "abc"})
        self.assertIsNone(route.match("GET", ["v1", "notebooks", "abc", "ask"]))
        self.assertIsNone(route.match("POST", ["v1", "notebooks", "abc"]))


class OcrSolvePathTests(unittest.TestCase):
    def test_ocr_payload_solves(self) -> None:
        api = StudyLabAPI()
        payload = base64.b64encode(b"What is 3 + 4?").decode("utf-8")
        result = api.solve(payload, input_type="image", subject="analytics")
        self.assertTrue(result["verified"])
        self.assertEqual(result["answer"], "7")


if __name__ == "__main__":
    unittest.main()
