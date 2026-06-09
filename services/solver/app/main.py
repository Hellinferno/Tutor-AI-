from __future__ import annotations

from studylab_core import InMemoryStudyLabStore, RagEngine, SolverEngine, StudyLabAPI, make_store_from_env
from studylab_core.service_http import Route, serve


def create_solver_engine() -> SolverEngine:
    store = InMemoryStudyLabStore()
    return SolverEngine(store=store, rag=RagEngine(store))


api = StudyLabAPI(make_store_from_env())


ROUTES = [
    Route(
        "POST",
        "/v1/solve",
        lambda p, b: api.solve(
            content=b["content"],
            subject=b.get("subject", "ai_ds"),
            input_type=b.get("input_type", "text"),
            notebook_id=b.get("notebook_id"),
        ),
    ),
    Route("POST", "/v1/solve/{solution_id}/reveal", lambda p, b: api.reveal(solution_id=p["solution_id"], step_idx=int(b["step_idx"]))),
]


def main() -> None:
    serve("StudyLabSolver/0.1", ROUTES, env_port="SOLVER_PORT", default_port=8002)


if __name__ == "__main__":
    main()
