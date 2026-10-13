import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, flash, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from flask_wtf.csrf import CSRFProtect, CSRFError
from extensions import limiter
from core.logger import get_logger

logger = get_logger(__name__)

from services.db_service import DatabaseService
from services.tmdb_service import TmdbService
from services.auth_service import AuthService
from core.motor_recomendacion import MotorRecomendacion
from core.motor_explicacion import MotorExplicacion
from routes import busqueda_routes, recomendacion_routes, auth_routes, payment_routes, historial_routes

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

# ---------------------------------------------------------------------------
# Inicializacion de servicios
# ---------------------------------------------------------------------------

IS_PRODUCTION = os.getenv('FLASK_ENV', 'development') != 'development'

# En produccion los secretos son obligatorios: sin ellos las sesiones, el cifrado
# AES (Fernet) y las firmas HMAC quedarian protegidos por valores publicos del repo.
if IS_PRODUCTION:
    _faltantes = [k for k in ('FLASK_SECRET_KEY', 'JWT_SECRET') if not os.getenv(k)]
    if _faltantes:
        raise RuntimeError(f"Faltan variables de entorno obligatorias en produccion: {', '.join(_faltantes)}")

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'guaugle_movies_v3_final_dev_only')

# Detras de proxies (Netlify -> Render) la IP real llega en X-Forwarded-For.
# Sin esto el rate limiting contaria todas las peticiones como una sola IP.
if IS_PRODUCTION:
    from werkzeug.middleware.proxy_fix import ProxyFix
    _hops = int(os.getenv('PROXY_HOPS', '1'))
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=_hops, x_proto=1, x_host=1)

# Configuración de cookie de sesión segura
app.config['SESSION_COOKIE_HTTPONLY'] = True   # Inaccesible desde JS (protege contra XSS)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Protege contra CSRF en navegadores modernos
app.config['SESSION_COOKIE_SECURE'] = IS_PRODUCTION  # HTTPS solo en prod

# CSRF: protege rutas HTML contra Cross-Site Request Forgery
# Los endpoints /api/* quedan excluidos (usan JSON + SameSite=Lax, no son vulnerables)
csrf = CSRFProtect(app)

# Rate limiting: inicializar con la app (el objeto limiter viene de extensions.py)
limiter.init_app(app)

db   = DatabaseService(os.getenv('DATABASE_URL', ''))
tmdb = TmdbService(db_service=db)

if tmdb.is_ready():
    print("TMDB API habilitada.")
else:
    print("TMDB API no habilitada: define TMDB_API_KEY para activar datos live.")

motor     = MotorRecomendacion()
explicador = MotorExplicacion()
auth      = AuthService(db_service=db, jwt_secret=os.getenv('JWT_SECRET'))

# ---------------------------------------------------------------------------
# Registro de rutas
# ---------------------------------------------------------------------------

busqueda_routes.register(app, tmdb)
recomendacion_routes.register(app, tmdb, motor, explicador, auth_service=auth)
auth_routes.register(app, auth, limiter=limiter, csrf=csrf)
payment_routes.register(app, db, csrf=csrf)
historial_routes.register(app, db, csrf=csrf)

# Eximir blueprints de búsqueda y recomendación del CSRF (son todos endpoints JSON/API)
from routes.busqueda_routes import bp as bp_busqueda
from routes.recomendacion_routes import bp as bp_reco
csrf.exempt(bp_busqueda)
csrf.exempt(bp_reco)
from routes.auth_routes import bp as bp_auth
csrf.exempt(bp_auth)
from routes.historial_routes import bp as bp_historial
csrf.exempt(bp_historial)

# ---------------------------------------------------------------------------
# Rutas generales
# ---------------------------------------------------------------------------

@app.errorhandler(CSRFError)
def csrf_error_handler(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Token CSRF inválido o ausente.'}), 400
    flash('Formulario inválido. Recarga la página e inténtalo de nuevo.', 'error')
    return redirect(request.referrer or url_for('index'))


@app.errorhandler(429)
def ratelimit_handler(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Demasiados intentos. Espera un momento antes de volver a intentarlo.'}), 429
    return render_template('errors/429.html'), 429


@app.after_request
def security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response


@app.before_request
def proteger_sesion():
    try:
        _ = session.get('historial', [])
    except Exception:
        logger.warning('Sesión corrupta detectada — limpiando', exc_info=True)
        session.clear()


@app.route('/favicon.ico')
def favicon_ico():
    return redirect(url_for('favicon_svg'))


@app.route('/favicon.svg')
def favicon_svg():
    return send_from_directory(BASE_DIR / 'frontend' / 'public', 'favicon.svg')


@app.route('/')
def index():
    top_10 = tmdb.get_popular(page=1)[:10] if tmdb.is_ready() else []
    try:
        historial = session.get('historial', [])
        session['historial'] = historial
    except Exception:
        logger.warning('Error al leer historial de sesión — reseteando', exc_info=True)
        historial = []
        session['historial'] = []

    usuario_actual = auth.get_usuario_actual(session)
    return render_template(
        'index.html',
        top_10=top_10,
        recomendados=[],
        recomendados_sec=[],
        tipo_sec='',
        historial=historial,
        ultima_peli=session.get('ultima_peli', None),
        usuario=usuario_actual,
    )


@app.route('/api/home')
def api_home():
    """Datos iniciales para React: top_10 populares. El historial viene de /api/usuario/historial."""
    top_10 = tmdb.get_popular(page=1)[:10] if tmdb.is_ready() else []
    return jsonify({
        'top_10':    top_10,
        'historial': [],  # siempre vacío: el frontend usa /api/usuario/historial (BD)
        'ultima_peli': session.get('ultima_peli'),
    })


@app.route('/healthz')
def healthz():
    """Health check para la plataforma de hosting."""
    return jsonify({'status': 'ok', 'db': db.is_ready(), 'tmdb': tmdb.is_ready()})


@app.route('/limpiar')
def limpiar_sesion():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    # use_reloader=False es necesario para que Flask-Limiter con storage memory://
    # acumule correctamente los contadores entre peticiones (el reloader genera
    # dos procesos con memorias separadas, lo que rompe el rate limiting en dev).
    app.run(debug=True, use_reloader=False)
