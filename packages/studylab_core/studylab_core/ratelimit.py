from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

# In-memory sliding-window rate limiter. Dependency-free and per-process — a real
# deployment would use Redis for a shared window, but this gives correct, testable
# limiting for a single gateway and an obvious seam to swap. Disabled unless a limit
# is configured (STUDYLAB_RATE_LIMIT="requests/seconds", e.g. "120/60").


class RateLimitError(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after}s.")


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        """Record a hit for ``key``; raise RateLimitError if it exceeds the window."""
        now = time.time()
        cutoff = now - self.window_seconds
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] < cutoff:
                hits.popleft()
            if len(hits) >= self.max_requests:
                retry_after = max(1, int(self.window_seconds - (now - hits[0])))
                raise RateLimitError(retry_after)
            hits.append(now)


def make_rate_limiter_from_env(spec: str | None) -> RateLimiter | None:
    """Build a limiter from a ``"requests/seconds"`` spec, or None to disable."""
    if not spec:
        return None
    try:
        requests_s, window_s = spec.split("/", 1)
        max_requests = int(requests_s)
        window_seconds = int(window_s)
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"Invalid rate-limit spec '{spec}'; expected 'requests/seconds' (e.g. '120/60')") from exc
    if max_requests <= 0 or window_seconds <= 0:
        return None
    return RateLimiter(max_requests, window_seconds)
