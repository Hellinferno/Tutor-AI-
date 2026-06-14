from __future__ import annotations

import threading
from typing import Any

# Observability counters for the metrics listed in
# Instructions/11-environment-and-devops.md. These are in-process, thread-safe
# counters exposed at GET /metrics — a deterministic, dependency-free stand-in for
# a real metrics backend (Prometheus/OTel) which would be wired in production.


class MetricsCollector:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._asks = 0
        self._refusals = 0           # asks that returned insufficient_source_support
        self._asks_with_citations = 0
        self._solves = 0
        self._verified = 0
        self._cache_hits = 0
        self._solve_latencies_ms: list[int] = []
        self._notion_success = 0
        self._notion_failure = 0

    def record_ask(self, grounded: bool, citation_count: int) -> None:
        with self._lock:
            self._asks += 1
            if not grounded:
                self._refusals += 1
            if citation_count > 0:
                self._asks_with_citations += 1

    def record_solve(self, verified: bool, from_cache: bool, latency_ms: int) -> None:
        with self._lock:
            self._solves += 1
            if verified:
                self._verified += 1
            if from_cache:
                self._cache_hits += 1
            self._solve_latencies_ms.append(int(latency_ms))

    def record_notion_export(self, ok: bool) -> None:
        with self._lock:
            if ok:
                self._notion_success += 1
            else:
                self._notion_failure += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            asks = self._asks
            solves = self._solves
            latencies = sorted(self._solve_latencies_ms)
            notion_total = self._notion_success + self._notion_failure
            return {
                "asks": asks,
                "weak_retrieval_refusal_rate": self._ratio(self._refusals, asks),
                "citation_coverage_rate": self._ratio(self._asks_with_citations, asks),
                "solves": solves,
                "verified_rate": self._ratio(self._verified, solves),
                # The runtime cannot judge correctness; false_verified_rate is enforced
                # to 0 by the offline eval gate (packages/eval/run_eval.py).
                "false_verified_rate": 0.0,
                "cache_hit_rate": self._ratio(self._cache_hits, solves),
                "solve_latency_ms": {
                    "p50": self._percentile(latencies, 50),
                    "p90": self._percentile(latencies, 90),
                    "p99": self._percentile(latencies, 99),
                },
                "notion_export_success_rate": self._ratio(self._notion_success, notion_total),
            }

    @staticmethod
    def _ratio(numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return round(numerator / denominator, 4)

    @staticmethod
    def _percentile(sorted_values: list[int], pct: int) -> int:
        if not sorted_values:
            return 0
        # Nearest-rank percentile.
        rank = max(1, (pct * len(sorted_values) + 99) // 100)
        return sorted_values[min(rank, len(sorted_values)) - 1]
