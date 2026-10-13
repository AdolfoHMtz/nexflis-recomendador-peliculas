# Guía de despliegue

Arquitectura: **Netlify** (React) → proxy `/api/*` → **Render** (Flask) → **Neon** (PostgreSQL) + **TMDB**.

El proxy de Netlify hace que navegador y API compartan dominio, por lo que la cookie de sesión HttpOnly funciona sin CORS ni cookies de terceros.

## 1. Base de datos — Neon (gratis)

1. Crea un proyecto en <https://neon.tech> y copia la *connection string*.
2. Asegúrate de que termine en `?sslmode=require`.
3. **No necesitas ejecutar SQL**: `DatabaseService` crea y migra las tablas al arrancar (`schema.sql` es solo referencia).

Alternativa: Supabase (Settings → Database → connection string, modo *session pooler*).

## 2. Backend — Render

1. En <https://render.com> → **New → Blueprint** y selecciona este repositorio (lee `render.yaml`).
2. Completa las variables marcadas como secretas:
   - `DATABASE_URL` → la de Neon.
   - `TMDB_API_KEY` → tu key de TMDB.
   - `FLASK_SECRET_KEY` y `JWT_SECRET` se generan solas.
3. Verifica `https://<tu-servicio>.onrender.com/healthz` → `{"status":"ok","db":true,"tmdb":true}`.

> El plan gratuito de Render duerme el servicio tras ~15 min sin tráfico; la primera petición tarda ~30-60 s.

> **Importante:** `FLASK_SECRET_KEY` deriva la llave AES de los pagos y del historial cifrado. Si la cambias, los comprobantes y XML anteriores dejan de poder descifrarse.

## 3. Frontend — Netlify

1. En <https://app.netlify.com> → **Add new site → Import from Git** y elige el repositorio. Netlify lee `netlify.toml` (base `frontend`, publish `dist`).
2. En `netlify.toml`, cambia `https://nexflis-api.onrender.com` por la URL real de tu servicio de Render si es distinta, y haz push.

## 4. Verificación

- Abre el sitio de Netlify → registra un usuario → busca una película → reacciona y revisa la explicación.
- Si el login falla con 429 constantemente, revisa `PROXY_HOPS` (Netlify + Render = `2`).
