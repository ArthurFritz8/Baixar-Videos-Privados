from threading import RLock


class MetricsRegistry:
    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled
        self._counters: dict[str, int] = {}
        self._gauges: dict[str, float] = {}
        self._lock = RLock()

    def inc_counter(self, name: str, value: int = 1) -> None:
        if not self._enabled:
            return
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + value

    def set_gauge(self, name: str, value: float) -> None:
        if not self._enabled:
            return
        with self._lock:
            self._gauges[name] = value

    def snapshot(self) -> dict[str, dict[str, float | int]]:
        with self._lock:
            return {
                "enabled": {"value": 1 if self._enabled else 0},
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
            }
