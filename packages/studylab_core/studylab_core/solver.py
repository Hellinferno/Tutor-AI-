from __future__ import annotations

import ast
import hashlib
import operator
import re
import time
from typing import Any

from .models import Citation, Solution, SolveResponse
from .rag import RagEngine
from .sandbox import extract_code, run_code
from .store import InMemoryStudyLabStore


ALLOWED_OPERATORS: dict[type[Any], Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def normalize_question(question: str) -> str:
    cleaned = re.sub(r"\s+", " ", question.lower()).strip()
    return re.sub(r"[^\w\s.%+-]", "", cleaned)


def question_hash(question: str) -> str:
    return hashlib.sha256(normalize_question(question).encode("utf-8")).hexdigest()


def _eval_numeric_node(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval_numeric_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and type(node.op) in ALLOWED_OPERATORS:
        return ALLOWED_OPERATORS[type(node.op)](_eval_numeric_node(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in ALLOWED_OPERATORS:
        left = _eval_numeric_node(node.left)
        right = _eval_numeric_node(node.right)
        return float(ALLOWED_OPERATORS[type(node.op)](left, right))
    raise ValueError("Unsupported expression")


def try_symbolic(question: str) -> tuple[bool, str | None]:
    candidates = [
        match.group(1).strip()
        for match in re.finditer(r"([-+*/().\d\s^]+)", question.replace("^", "**"))
        if re.search(r"\d", match.group(1))
    ]
    if not candidates:
        return False, None
    expression = max(candidates, key=len)
    if not expression or not re.search(r"\d", expression):
        return False, None
    try:
        parsed = ast.parse(expression, mode="eval")
        value = _eval_numeric_node(parsed)
    except Exception:
        return False, None
    formatted = str(round(value, 6)).rstrip("0").rstrip(".")
    return True, formatted


def try_finance_formula(question: str) -> tuple[bool, str | None]:
    lowered = question.lower()
    if "npv" not in lowered and "net present value" not in lowered:
        return False, None
    rate_match = re.search(r"(\d+(?:\.\d+)?)\s*%", lowered)
    if not rate_match:
        return False, None
    rate = float(rate_match.group(1)) / 100
    cash_flow_text = lowered.split("cash flow", 1)[-1]
    cash_flows = [float(value) for value in re.findall(r"[-+]?\d+(?:\.\d+)?", cash_flow_text)]
    cash_flows = [value for value in cash_flows if value != float(rate_match.group(1))]
    if len(cash_flows) < 2:
        return False, None
    npv = sum(cash_flow / ((1 + rate) ** index) for index, cash_flow in enumerate(cash_flows))
    return True, str(round(npv, 2))


class SolverEngine:
    def __init__(self, store: InMemoryStudyLabStore, rag: RagEngine | None = None) -> None:
        self.store = store
        self.rag = rag

    def solve(self, question: str, subject: str = "ai_ds", notebook_id: str | None = None) -> SolveResponse:
        started = time.perf_counter()
        q_hash = question_hash(question)
        cached = self.store.get_cached_solution(q_hash)
        if cached:
            return self._to_response(cached, from_cache=True, started=started)

        citations: list[Citation] = []
        if notebook_id and self.rag:
            citations = self.rag.retrieve(notebook_id=notebook_id, query=question)

        verified, answer, verify_method = self._solve_uncached(question=question, subject=subject, citations=citations)
        question_id = self.store.next_id("question")
        steps = self._make_steps(question=question, answer=answer, verified=verified, verify_method=verify_method)
        solution = Solution(
            id=self.store.next_id("solution"),
            question_id=question_id,
            question_hash=q_hash,
            answer=answer,
            steps=steps,
            verified=verified,
            verify_method=verify_method,
            citations=citations,
        )
        self.store.add_solution(solution)
        return self._to_response(solution, from_cache=False, started=started)

    def reveal_step(self, solution_id: str, step_idx: int) -> dict[str, Any]:
        solution = self.store.require_solution(solution_id)
        for step in solution.steps:
            if step["idx"] == step_idx:
                step["revealed"] = True
                self.store.save_solution(solution)
                return step
        raise IndexError(f"Step {step_idx} not found")

    def _solve_uncached(
        self,
        question: str,
        subject: str,
        citations: list[Citation],
    ) -> tuple[bool, str, str]:
        # Executable code is checked first: a snippet like ``print(6*7)`` must run
        # in the sandbox rather than be scraped for stray numbers by the symbolic path.
        code = extract_code(question)
        if code is not None:
            verdict = run_code(code)
            if verdict.ok:
                return True, verdict.output, "code_exec"
            return False, f"Code could not be verified by the sandbox: {verdict.reason}", "unverified"

        finance_ok, finance_answer = try_finance_formula(question)
        if finance_ok and finance_answer is not None:
            return True, finance_answer, "formula"

        symbolic_ok, symbolic_answer = try_symbolic(question)
        if symbolic_ok and symbolic_answer is not None:
            return True, symbolic_answer, "symbolic"

        if citations:
            return (
                False,
                "This is a conceptual source-grounded answer. I can cite supporting material, but it is not objectively verifiable.",
                "unverified",
            )

        return False, "I can provide a general explanation, but this answer is not verified by an objective checker.", "unverified"

    def _make_steps(self, question: str, answer: str, verified: bool, verify_method: str) -> list[dict[str, Any]]:
        return [
            {"idx": 0, "text": f"Normalize and classify the question: {normalize_question(question)}", "revealed": True},
            {"idx": 1, "text": f"Compute or draft the answer: {answer}", "revealed": False},
            {
                "idx": 2,
                "text": f"Verification result: {'passed' if verified else 'not verified'} via {verify_method}.",
                "revealed": False,
            },
        ]

    def _to_response(self, solution: Solution, from_cache: bool, started: float) -> SolveResponse:
        return SolveResponse(
            question_id=solution.question_id,
            solution_id=solution.id,
            answer=solution.answer,
            steps=solution.steps,
            verified=solution.verified,
            verify_method=solution.verify_method,
            from_cache=from_cache,
            citations=solution.citations,
            latency_ms=max(1, int((time.perf_counter() - started) * 1000)),
        )
