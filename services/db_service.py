import json
import hashlib
import time
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

from core.logger import get_logger

try:
    import psycopg2
    from psycopg2 import pool as _pg_pool
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
    _pg_pool = None
    RealDictCursor = None

logger = get_logger(__name__)


_POOL_MAX = 20
_LAST_USED = {}  # id(conexion) -> instante del ultimo uso (psycopg2 no admite atributos)
_IDLE_CHECK_SECONDS = 30


class _SimplePool:
    """Pool minimo y thread-safe que CONSERVA las conexiones libres.

    psycopg2.ThreadedConnectionPool solo mantiene `minconn` libres y cierra el
    resto, lo que obligaba a reconectar en cada consulta concurrente.
    """

    def __init__(self, dsn, maxsize):
        self._dsn = dsn
        self._idle = []
        self._lock = threading.Lock()
        self._sem = threading.BoundedSemaphore(maxsize)

    def getconn(self):
        if not self._sem.acquire(timeout=10):
            raise RuntimeError('connection pool exhausted')
        try:
            with self._lock:
                raw = self._idle.pop() if self._idle else None
            return raw if raw is not None else psycopg2.connect(self._dsn)
        except Exception:
            self._sem.release()
            raise

    def putconn(self, raw, close=False):
        try:
            if close or raw.closed:
                try:
                    raw.close()
                except Exception:
                    pass
            else:
                with self._lock:
                    self._idle.append(raw)
        finally:
            self._sem.release()


class _PooledConn:
    """Envoltorio de conexion: close() la devuelve al pool en vez de cerrarla.

    Mantiene intacta la API usada por el servicio (`with conn:`, `conn.cursor()`,
    `conn.close()`), asi evitar abrir TCP+TLS hacia la BD en cada consulta.
    """

    def __init__(self, raw, pool_ref):
        self._raw = raw
        self._pool = pool_ref
        self._released = False

    def __getattr__(self, name):
        return getattr(self._raw, name)

    def __enter__(self):
        return self._raw.__enter__()

    def __exit__(self, *exc):
        return self._raw.__exit__(*exc)

    def close(self):
        if self._released:
            return
        self._released = True
        try:
            if self._pool is None:
                self._raw.close()
                return
            if self._raw.closed:
                self._pool.putconn(self._raw, close=True)
                return
            try:
                self._raw.rollback()
            except Exception:
                self._pool.putconn(self._raw, close=True)
                return
            _LAST_USED[id(self._raw)] = time.monotonic()
            self._pool.putconn(self._raw)
        except Exception:
            logger.debug('No se pudo devolver la conexion al pool', exc_info=True)

    def __del__(self):
        # Red de seguridad: rutas con excepcion que no llegaron a close().
        try:
            self.close()
        except Exception:
            pass


class DatabaseService:
    """Servicio de acceso a PostgreSQL.

    Centraliza todas las operaciones de base de datos.
    Actualmente maneja:
      - Cache persistente de TMDB (tabla tmdb_cache)
    En fases posteriores manejara:
      - Usuarios, historial, dimensiones de peliculas
    """

    def __init__(self, db_url: str):
        self._db_url = db_url
        self._ready = False
        self._pool = None
        self._clasif_vistas = {}
        self._pool_lock = threading.Lock()
        if db_url and psycopg2:
            self._ensure_cache_table()
            self._ensure_users_table()
            self._ensure_peliculas_table()
            self._ensure_historial_table()
            self._ensure_ultima_consulta_table()
            self._ensure_transacciones_table()

    def is_ready(self) -> bool:
        return self._ready

    # ------------------------------------------------------------------
    # Conexion
    # ------------------------------------------------------------------

    def _get_pool(self):
        if self._pool is None:
            with self._pool_lock:
                if self._pool is None and psycopg2 is not None:
                    self._pool = _SimplePool(self._db_url, _POOL_MAX)
        return self._pool

    def _connect(self):
        """Devuelve una conexion del pool (cae a conexion directa si el pool falla)."""
        if not self._db_url or not psycopg2:
            return None
        try:
            pool = self._get_pool()
            if pool is None:
                return _PooledConn(psycopg2.connect(self._db_url), None)
            raw = pool.getconn()
            last = _LAST_USED.get(id(raw))
            stale = raw.closed or (last is not None and time.monotonic() - last > _IDLE_CHECK_SECONDS)
            if stale and not raw.closed:
                try:
                    with raw.cursor() as cur:
                        cur.execute('SELECT 1')
                    raw.rollback()
                except Exception:
                    pool.putconn(raw, close=True)
                    raw = pool.getconn()
            elif raw.closed:
                pool.putconn(raw, close=True)
                raw = pool.getconn()
            return _PooledConn(raw, pool)
        except Exception:
            logger.warning('Pool de conexiones no disponible, usando conexion directa', exc_info=True)
            return _PooledConn(psycopg2.connect(self._db_url), None)

    def _ensure_tables(self) -> None:
        """Alias publico para _ensure_cache_table + _ensure_users_table."""
        self._ensure_cache_table()
        self._ensure_users_table()

    def _ensure_users_table(self) -> None:
        try:
            conn = self._connect()
            if not conn:
                return
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS users (
                            id            SERIAL PRIMARY KEY,
                            username      TEXT UNIQUE NOT NULL,
                            password_hash TEXT NOT NULL,
                            email         TEXT,
                            edad          INT,
                            rol           TEXT NOT NULL DEFAULT 'user',
                            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        );
                        """
                    )
                    # Migraciones no destructivas
                    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT;")
                    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS plan TEXT NOT NULL DEFAULT 'free';")
                    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_expires_at TIMESTAMPTZ DEFAULT NULL;")
                    # Índice UNIQUE parcial en email (ignora NULLs)
                    cur.execute("""
                        DO $$
                        BEGIN
                            IF NOT EXISTS (
                                SELECT 1 FROM pg_indexes WHERE indexname = 'users_email_unique'
                            ) THEN
                                CREATE UNIQUE INDEX users_email_unique ON users(email)
                                WHERE email IS NOT NULL;
                            END IF;
                        END $$;
                    """)
            conn.close()
        except Exception:
            logger.error('Error al crear/migrar tabla users', exc_info=True)

    def _ensure_peliculas_table(self) -> None:
        try:
            conn = self._connect()
            if not conn:
                return
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS peliculas (
                            id                BIGINT PRIMARY KEY,
                            titulo            TEXT NOT NULL,
                            clasificacion_edad INT NOT NULL DEFAULT 0,
                            adult             BOOLEAN NOT NULL DEFAULT FALSE,
                            updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        );
                        """
                    )
            conn.close()
        except Exception:
            logger.error('Error al crear tabla peliculas', exc_info=True)

    def _ensure_cache_table(self) -> None:
        try:
            conn = self._connect()
            if not conn:
                return
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS tmdb_cache (
                            cache_key TEXT PRIMARY KEY,
                            payload JSONB NOT NULL,
                            expires_at TIMESTAMPTZ NOT NULL,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        );
                        """
                    )
            conn.close()
            self._ready = True
        except Exception:
            logger.error('Error al crear tabla tmdb_cache — DB no disponible', exc_info=True)
            self._ready = False

    # ------------------------------------------------------------------
    # Cache persistente TMDB
    # ------------------------------------------------------------------

    @staticmethod
    def cache_key(path: str, params: dict) -> str:
        raw = f"{path}|{json.dumps(params, sort_keys=True, ensure_ascii=False)}"
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    def cache_get(self, key: str) -> Optional[Any]:
        if not self._ready:
            return None
        try:
            conn = self._connect()
            if not conn:
                return None
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT payload, expires_at FROM tmdb_cache WHERE cache_key=%s",
                        (key,)
                    )
                    row = cur.fetchone()
            conn.close()
            if not row:
                return None
            if row['expires_at'] <= datetime.now(timezone.utc):
                return None
            return row['payload']
        except Exception:
            logger.error('cache_get falló para key=%s', key, exc_info=True)
            return None

    def cache_set(self, key: str, payload: Any, ttl_seconds: int) -> None:
        if not self._ready:
            return
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        try:
            conn = self._connect()
            if not conn:
                return
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO tmdb_cache (cache_key, payload, expires_at)
                        VALUES (%s, %s::jsonb, %s)
                        ON CONFLICT (cache_key)
                        DO UPDATE SET payload=EXCLUDED.payload, expires_at=EXCLUDED.expires_at;
                        """,
                        (key, json.dumps(payload, ensure_ascii=False), expires_at)
                    )
            conn.close()
        except Exception:
            logger.error('cache_set falló para key=%s', key, exc_info=True)

    # ------------------------------------------------------------------
    # Usuarios
    # ------------------------------------------------------------------

    def get_user_by_username(self, username: str) -> Optional[dict]:
        if not self._ready:
            return None
        try:
            conn = self._connect()
            if not conn:
                return None
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT id, username, password_hash, email, edad, rol FROM users WHERE username=%s",
                        (username,)
                    )
                    row = cur.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception:
            logger.error('get_user_by_username falló para username=%s', username, exc_info=True)
            return None

    def get_user_by_email(self, email: str) -> Optional[dict]:
        if not self._ready:
            return None
        try:
            conn = self._connect()
            if not conn:
                return None
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT id, username, password_hash, email, edad, rol FROM users WHERE email=%s LIMIT 1",
                        (email,)
                    )
                    row = cur.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception:
            logger.error('get_user_by_email falló para email=%s', email, exc_info=True)
            return None

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        if not self._ready:
            return None
        try:
            conn = self._connect()
            if not conn:
                return None
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT id, username, password_hash, email, edad, rol FROM users WHERE id=%s",
                        (user_id,)
                    )
                    row = cur.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception:
            logger.error('get_user_by_id falló para user_id=%s', user_id, exc_info=True)
            return None

    # ------------------------------------------------------------------
    # Peliculas - clasificacion de edad
    # ------------------------------------------------------------------

    def upsert_pelicula_clasificacion(self, movie_id: int, titulo: str, clasificacion_edad: int, adult: bool) -> None:
        """Persiste o actualiza la clasificacion de edad de una pelicula."""
        if not self._ready:
            return
        firma = (movie_id, titulo, clasificacion_edad, bool(adult))
        vistas = self.__dict__.setdefault('_clasif_vistas', {})
        if vistas.get(movie_id) == firma:
            return
        try:
            conn = self._connect()
            if not conn:
                return
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO peliculas (id, titulo, clasificacion_edad, adult, updated_at)
                        VALUES (%s, %s, %s, %s, NOW())
                        ON CONFLICT (id)
                        DO UPDATE SET
                            titulo             = EXCLUDED.titulo,
                            clasificacion_edad = EXCLUDED.clasificacion_edad,
                            adult              = EXCLUDED.adult,
                            updated_at         = NOW();
                        """,
                        (movie_id, titulo, clasificacion_edad, adult)
                    )
            conn.close()
            vistas[movie_id] = firma
        except Exception:
            logger.error('upsert_pelicula_clasificacion falló para movie_id=%s', movie_id, exc_info=True)

    def get_clasificacion_edad(self, movie_id: int) -> Optional[dict]:
        """Retorna {'clasificacion_edad': int, 'adult': bool} o None si no existe."""
        if not self._ready:
            return None
        try:
            conn = self._connect()
            if not conn:
                return None
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT clasificacion_edad, adult FROM peliculas WHERE id=%s",
                        (movie_id,)
                    )
                    row = cur.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception:
            logger.error('get_clasificacion_edad falló para movie_id=%s', movie_id, exc_info=True)
            return None

    def update_user(
        self,
        user_id: int,
        edad: Optional[int] = None,
        password_hash: Optional[str] = None,
        email: Optional[str] = None,
        username: Optional[str] = None,
    ) -> Optional[dict]:
        """Actualiza campos del usuario. Retorna la fila actualizada o None.

        Campos soportados: edad, password_hash, email, username.
        Si username o email ya existen en otro usuario, retorna None (violación UNIQUE).
        """
        if not self._ready:
            return None
        sets = []
        vals = []
        if edad is not None:
            sets.append("edad = %s")
            vals.append(edad)
        if password_hash is not None:
            sets.append("password_hash = %s")
            vals.append(password_hash)
        if email is not None:
            sets.append("email = %s")
            vals.append(email if email else None)
        if username is not None:
            sets.append("username = %s")
            vals.append(username)
        if not sets:
            return self.get_user_by_id(user_id)
        vals.append(user_id)
        try:
            conn = self._connect()
            if not conn:
                return None
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        f"UPDATE users SET {', '.join(sets)} WHERE id=%s RETURNING id, username, email, edad, rol",
                        vals
                    )
                    row = cur.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as exc:
            if psycopg2 and isinstance(exc, psycopg2.errors.UniqueViolation):
                logger.warning('update_user: conflicto de unicidad para user_id=%s', user_id)
                return None
            logger.error('update_user falló para user_id=%s', user_id, exc_info=True)
            return None

    # ------------------------------------------------------------------
    # Historial de visionado
    # ------------------------------------------------------------------

    def _ensure_historial_table(self) -> None:
        try:
            conn = self._connect()
            if not conn:
                return
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS historial_usuarios (
                            id             BIGSERIAL PRIMARY KEY,
                            usuario_id     INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                            pelicula_id    BIGINT NOT NULL,
                            titulo         TEXT NOT NULL DEFAULT '',
                            poster_path    TEXT NOT NULL DEFAULT '',
                            minutos_vistos INT NOT NULL DEFAULT 0,
                            duracion_total INT NOT NULL DEFAULT 0,
                            reaccion       TEXT NOT NULL DEFAULT 'like',
                            datos_pelicula JSONB,
                            viewed_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            UNIQUE (usuario_id, pelicula_id)
                        );
                        CREATE INDEX IF NOT EXISTS idx_historial_usuario_fecha
                            ON historial_usuarios(usuario_id, viewed_at DESC);
                        """
                    )
                    # Migración no destructiva: añadir constraint único si la tabla ya existía sin él.
                    # Primero eliminamos duplicados (conservando el más reciente por viewed_at),
                    # luego añadimos el constraint. Si ya existe, no hace nada.
                    cur.execute(
                        """
                        DO $$
                        BEGIN
                            IF NOT EXISTS (
                                SELECT 1 FROM pg_constraint
                                WHERE conname = 'historial_usuarios_usuario_id_pelicula_id_key'
                            ) THEN
                                -- Eliminar duplicados: conservar solo la fila con el id más alto (más reciente)
                                DELETE FROM historial_usuarios h
                                WHERE h.id NOT IN (
                                    SELECT MAX(h2.id)
                                    FROM historial_usuarios h2
                                    GROUP BY h2.usuario_id, h2.pelicula_id
                                );
                                ALTER TABLE historial_usuarios
                                    ADD CONSTRAINT historial_usuarios_usuario_id_pelicula_id_key
                                    UNIQUE (usuario_id, pelicula_id);
                            END IF;
                        END $$;
                        """
                    )
            conn.close()
        except Exception:
            logger.error('Error al crear/migrar tabla historial_usuarios', exc_info=True)

    def guardar_visionado(self, usuario_id: int, interaccion: dict) -> bool:
        """Guarda o actualiza un visionado en historial_usuarios (UPSERT por usuario+pelicula)."""
        if not self._ready:
            return False
        self._ensure_historial_table()
        try:
            conn = self._connect()
            if not conn:
                return False
            import json as _json
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO historial_usuarios
                            (usuario_id, pelicula_id, titulo, poster_path, minutos_vistos, duracion_total, reaccion, datos_pelicula, viewed_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, NOW())
                        ON CONFLICT (usuario_id, pelicula_id)
                        DO UPDATE SET
                            titulo         = EXCLUDED.titulo,
                            poster_path    = EXCLUDED.poster_path,
                            minutos_vistos = EXCLUDED.minutos_vistos,
                            duracion_total = EXCLUDED.duracion_total,
                            reaccion       = EXCLUDED.reaccion,
                            datos_pelicula = EXCLUDED.datos_pelicula,
                            viewed_at      = NOW();
                        """,
                        (
                            usuario_id,
                            int(interaccion.get('id', 0)),
                            str(interaccion.get('title', '')),
                            str(interaccion.get('poster_path', '')),
                            int(interaccion.get('minutos_vistos', 0)),
                            int(interaccion.get('runtime', 0)),
                            str(interaccion.get('reaccion', 'like')),
                            _json.dumps(interaccion, ensure_ascii=False),
                        )
                    )
            conn.close()
            return True
        except Exception:
            logger.error('guardar_visionado falló para usuario_id=%s pelicula_id=%s',
                         usuario_id, interaccion.get('id'), exc_info=True)
            return False

    def obtener_historial_usuario(self, usuario_id: int, limit: int = 20) -> list:
        """Retorna las últimas `limit` películas vistas por el usuario (por defecto 20)."""
        if not self._ready:
            return []
        self._ensure_historial_table()
        try:
            conn = self._connect()
            if not conn:
                return []
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT datos_pelicula, minutos_vistos, duracion_total, reaccion, viewed_at
                        FROM historial_usuarios
                        WHERE usuario_id = %s
                        ORDER BY viewed_at DESC
                        LIMIT %s
                        """,
                        (usuario_id, limit)
                    )
                    rows = cur.fetchall()
            conn.close()
            historial = []
            for row in rows:
                datos = dict(row.get('datos_pelicula') or {})
                datos['minutos_vistos'] = row['minutos_vistos']
                datos['progreso'] = round(
                    (row['minutos_vistos'] / max(row['duracion_total'], 1)) * 100, 1
                ) if row['duracion_total'] > 0 else 0
                datos['reaccion'] = row['reaccion']
                datos['viewed_at'] = row['viewed_at'].isoformat() if row['viewed_at'] else None
                historial.append(datos)
            return historial
        except Exception:
            logger.error('obtener_historial_usuario falló para usuario_id=%s', usuario_id, exc_info=True)
            return []

    # ------------------------------------------------------------------
    # Última consulta de recomendación
    # ------------------------------------------------------------------

    def _ensure_ultima_consulta_table(self) -> None:
        try:
            conn = self._connect()
            if not conn:
                return
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS ultima_consulta_usuario (
                            usuario_id   INT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                            payload      JSONB NOT NULL,
                            updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        );
                        """
                    )
            conn.close()
        except Exception:
            logger.error('Error al crear tabla ultima_consulta_usuario', exc_info=True)

    def guardar_ultima_consulta(self, usuario_id: int, payload: dict) -> bool:
        """Guarda (UPSERT) la última respuesta de /api/recomendar para el usuario."""
        if not self._ready:
            return False
        self._ensure_ultima_consulta_table()
        try:
            conn = self._connect()
            if not conn:
                return False
            import json as _json
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO ultima_consulta_usuario (usuario_id, payload, updated_at)
                        VALUES (%s, %s::jsonb, NOW())
                        ON CONFLICT (usuario_id)
                        DO UPDATE SET payload = EXCLUDED.payload, updated_at = NOW();
                        """,
                        (usuario_id, _json.dumps(payload, ensure_ascii=False))
                    )
            conn.close()
            return True
        except Exception:
            logger.error('guardar_ultima_consulta falló para usuario_id=%s', usuario_id, exc_info=True)
            return False

    def obtener_ultima_consulta(self, usuario_id: int) -> Optional[dict]:
        """Retorna el payload de la última consulta del usuario, o None si no existe."""
        if not self._ready:
            return None
        self._ensure_ultima_consulta_table()
        try:
            conn = self._connect()
            if not conn:
                return None
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT payload FROM ultima_consulta_usuario WHERE usuario_id = %s",
                        (usuario_id,)
                    )
                    row = cur.fetchone()
            conn.close()
            return dict(row['payload']) if row else None
        except Exception:
            logger.error('obtener_ultima_consulta falló para usuario_id=%s', usuario_id, exc_info=True)
            return None

    def create_user(self, username: str, password_hash: str, edad: Optional[int], email: Optional[str] = None, rol: str = 'user') -> Optional[dict]:
        """Inserta un usuario nuevo y retorna su fila, o None si el username ya existe."""
        if not self._ready:
            return None
        try:
            conn = self._connect()
            if not conn:
                return None
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        INSERT INTO users (username, password_hash, email, edad, rol)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id, username, email, edad, rol
                        """,
                        (username, password_hash, email, edad, rol)
                    )
                    row = cur.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception:
            logger.error('create_user falló para username=%s', username, exc_info=True)
            return None

    # ------------------------------------------------------------------
    # Transacciones / Plan
    # ------------------------------------------------------------------

    def _ensure_transacciones_table(self) -> None:
        try:
            conn = self._connect()
            if not conn:
                return
            with conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS transacciones (
                            id              SERIAL PRIMARY KEY,
                            txn_id          TEXT UNIQUE NOT NULL,
                            usuario_id      INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                            plan            TEXT NOT NULL DEFAULT 'premium',
                            monto           NUMERIC(10,2) NOT NULL DEFAULT 9.99,
                            moneda          TEXT NOT NULL DEFAULT 'USD',
                            ultimos_digitos TEXT NOT NULL,
                            payload_cifrado TEXT NOT NULL,
                            hmac_firma      TEXT NOT NULL,
                            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            expires_at      TIMESTAMPTZ NOT NULL
                        );
                    """)
            conn.close()
        except Exception:
            logger.error('Error al crear tabla transacciones', exc_info=True)

    def crear_transaccion(self, txn_id: str, usuario_id: int, ultimos_digitos: str,
                          payload_cifrado: str, hmac_firma: str, expires_at) -> Optional[dict]:
        if not self._ready:
            return None
        try:
            conn = self._connect()
            if not conn:
                return None
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        INSERT INTO transacciones
                            (txn_id, usuario_id, ultimos_digitos, payload_cifrado, hmac_firma, expires_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING *
                    """, (txn_id, usuario_id, ultimos_digitos, payload_cifrado, hmac_firma, expires_at))
                    row = cur.fetchone()
                    # Actualizar plan del usuario
                    cur.execute("""
                        UPDATE users SET plan = 'premium', plan_expires_at = %s WHERE id = %s
                    """, (expires_at, usuario_id))
            conn.close()
            return dict(row) if row else None
        except Exception:
            logger.error('crear_transaccion falló para usuario_id=%s', usuario_id, exc_info=True)
            return None

    def eliminar_usuario(self, usuario_id: int) -> bool:
        """
        Elimina completamente al usuario y todos sus datos asociados.
        Las tablas con FK ON DELETE CASCADE limpian automáticamente
        historial, transacciones y última consulta.
        """
        if not self._ready:
            return False
        try:
            conn = self._connect()
            if not conn:
                return False
            with conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM users WHERE id = %s", (usuario_id,))
            conn.close()
            return True
        except Exception:
            logger.error('eliminar_usuario falló para usuario_id=%s', usuario_id, exc_info=True)
            return False

    def get_ultima_transaccion_usuario(self, usuario_id: int) -> Optional[dict]:
        if not self._ready:
            return None
        try:
            conn = self._connect()
            if not conn:
                return None
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT * FROM transacciones WHERE usuario_id=%s ORDER BY created_at DESC LIMIT 1",
                        (usuario_id,)
                    )
                    row = cur.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception:
            logger.error('get_ultima_transaccion_usuario falló para usuario_id=%s', usuario_id, exc_info=True)
            return None

    def get_transaccion(self, txn_id: str) -> Optional[dict]:
        if not self._ready:
            return None
        try:
            conn = self._connect()
            if not conn:
                return None
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT * FROM transacciones WHERE txn_id = %s",
                        (txn_id,)
                    )
                    row = cur.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception:
            logger.error('get_transaccion falló para txn_id=%s', txn_id, exc_info=True)
            return None

    def get_plan_usuario(self, usuario_id: int) -> dict:
        """Retorna plan y plan_expires_at del usuario, chequeando si expiró."""
        if not self._ready:
            return {'plan': 'free', 'plan_expires_at': None}
        try:
            conn = self._connect()
            if not conn:
                return {'plan': 'free', 'plan_expires_at': None}
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT plan, plan_expires_at FROM users WHERE id = %s",
                        (usuario_id,)
                    )
                    row = cur.fetchone()
            conn.close()
            if not row:
                return {'plan': 'free', 'plan_expires_at': None}
            # Si el plan expiró, degradar a free automáticamente
            plan = row['plan']
            expires = row['plan_expires_at']
            if plan == 'premium' and expires and expires < datetime.now(timezone.utc):
                self._degradar_a_free(usuario_id)
                return {'plan': 'free', 'plan_expires_at': None}
            return {'plan': plan, 'plan_expires_at': expires.isoformat() if expires else None}
        except Exception:
            logger.error('get_plan_usuario falló para usuario_id=%s', usuario_id, exc_info=True)
            return {'plan': 'free', 'plan_expires_at': None}

    def _degradar_a_free(self, usuario_id: int) -> None:
        try:
            conn = self._connect()
            if not conn:
                return
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE users SET plan = 'free', plan_expires_at = NULL WHERE id = %s",
                        (usuario_id,)
                    )
            conn.close()
        except Exception:
            logger.error('_degradar_a_free falló para usuario_id=%s', usuario_id, exc_info=True)
