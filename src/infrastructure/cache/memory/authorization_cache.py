from threading import RLock

from cachetools import TTLCache


class AuthorizationCache:
    def __init__(self, ttl_seconds: int, max_size: int) -> None:
        self._cache = TTLCache(maxsize=max_size, ttl=ttl_seconds)
        self._lock = RLock()

    def get(self, key: str) -> bool | None:
        with self._lock:
            value = self._cache.get(key)
            return bool(value) if value is not None else None

    def set(self, key: str, value: bool) -> None:
        with self._lock:
            self._cache[key] = value
