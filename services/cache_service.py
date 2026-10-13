import time
from typing import Any, Optional


class CacheService:
    """Cache en memoria con TTL por entrada.

    Reemplaza la logica de cache que estaba mezclada en TmdbService.
    No es persistente: se reinicia cuando el servidor se reinicia.
    Para cache persistente se usa tmdb_cache en PostgreSQL (gestionado por DatabaseService).
    """

    def __init__(self, ttl_segundos: int = 3600):
        self._ttl = ttl_segundos
        self._store: dict = {}
        self._timestamps: dict = {}

    def get(self, key: str) -> Optional[Any]:
        if key not in self._store:
            return None
        if time.time() - self._timestamps[key] > self._ttl:
            del self._store[key]
            del self._timestamps[key]
            return None
        return self._store[key]

    def set(self, key: str, value: Any, ttl_segundos: Optional[int] = None) -> None:
        ttl = ttl_segundos if ttl_segundos is not None else self._ttl
        self._store[key] = value
        self._timestamps[key] = time.time()
        # Guardar TTL personalizado junto a la entrada
        self._store[f'__ttl__{key}'] = ttl

    def delete(self, key: str) -> None:
        self._store.pop(key, None)
        self._timestamps.pop(key, None)
        self._store.pop(f'__ttl__{key}', None)

    def clear(self) -> None:
        self._store.clear()
        self._timestamps.clear()

    def _is_expired(self, key: str) -> bool:
        if key not in self._timestamps:
            return True
        ttl = self._store.get(f'__ttl__{key}', self._ttl)
        return time.time() - self._timestamps[key] > ttl
