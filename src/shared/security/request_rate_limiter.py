from collections import deque
from threading import RLock
from time import time

from src.shared.exceptions.errors import RateLimitExceededError


class RequesterRateLimiter:
    def __init__(
        self,
        enabled: bool,
        max_requests: int,
        window_seconds: int,
        public_failure_message: str,
    ) -> None:
        self._enabled = enabled
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._public_failure_message = public_failure_message
        self._events: dict[str, deque[float]] = {}
        self._lock = RLock()

    def consume(self, requester_id: str) -> None:
        if not self._enabled:
            return

        now = time()
        with self._lock:
            queue = self._events.setdefault(requester_id, deque())
            while queue and queue[0] <= now - self._window_seconds:
                queue.popleft()

            if len(queue) >= self._max_requests:
                raise RateLimitExceededError(
                    public_message=self._public_failure_message,
                    internal_detail=(
                        f"requester_rate_limited requester_id={requester_id} "
                        f"max={self._max_requests} window={self._window_seconds}"
                    ),
                )

            queue.append(now)
