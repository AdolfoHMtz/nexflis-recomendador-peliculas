-- NEXFLIS 2.0 - Schema base
-- Compatible con PostgreSQL
-- Incluye tablas actuales y extensiones previstas para fases siguientes.

CREATE TABLE IF NOT EXISTS tmdb_cache (
    cache_key   TEXT PRIMARY KEY,
    payload     JSONB NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    edad          INT,
    rol           TEXT NOT NULL DEFAULT 'user',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS peliculas (
    id              BIGINT PRIMARY KEY,
    titulo          TEXT NOT NULL,
    descripcion     TEXT,
    generos         JSONB,
    keywords        JSONB,
    actores         JSONB,
    director        TEXT,
    collection_id   BIGINT,
    collection_name TEXT,
    duracion        INT,
    rating          FLOAT,
    poster_url      TEXT,
    clasificacion_edad INT DEFAULT 0,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS historial_usuarios (
    id             BIGSERIAL PRIMARY KEY,
    usuario_id     INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pelicula_id    BIGINT NOT NULL REFERENCES peliculas(id) ON DELETE CASCADE,
    minutos_vistos INT DEFAULT 0,
    reaccion       TEXT,
    viewed_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dimensiones_peliculas (
    pelicula_id               BIGINT PRIMARY KEY REFERENCES peliculas(id) ON DELETE CASCADE,
    genero_primario           TEXT,
    generos_secundarios       JSONB,
    temas                     JSONB,
    dimensiones_explorables   JSONB,
    updated_at                TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS explicaciones_recomendacion (
    id                      BIGSERIAL PRIMARY KEY,
    usuario_id              INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pelicula_recomendada_id BIGINT NOT NULL REFERENCES peliculas(id) ON DELETE CASCADE,
    pelicula_referencia_id  BIGINT REFERENCES peliculas(id) ON DELETE SET NULL,
    tipo_rama               TEXT NOT NULL,
    score_final             FLOAT NOT NULL,
    explicacion             JSONB NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until             TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_tmdb_cache_expires ON tmdb_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_historial_usuario_fecha ON historial_usuarios(usuario_id, viewed_at DESC);
CREATE INDEX IF NOT EXISTS idx_historial_pelicula ON historial_usuarios(pelicula_id);
CREATE INDEX IF NOT EXISTS idx_dimensiones_genero ON dimensiones_peliculas(genero_primario);
CREATE INDEX IF NOT EXISTS idx_explicaciones_user_movie ON explicaciones_recomendacion(usuario_id, pelicula_recomendada_id);
