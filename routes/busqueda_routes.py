from flask import Blueprint, jsonify, request

from services.tmdb_service import TmdbService
from core.logger import get_logger

logger = get_logger(__name__)

bp = Blueprint('busqueda', __name__)
_tmdb: TmdbService = None


def register(app, tmdb_service: TmdbService):
    """Registra las rutas de busqueda en la app Flask."""
    global _tmdb
    _tmdb = tmdb_service
    app.register_blueprint(bp)


@bp.route('/api/buscar')
def api_buscar():
    """Endpoint AJAX para busqueda de peliculas con autocompletado."""
    q = request.args.get('q', '')
    resultados = _tmdb.search_movies(q, page=1)[:12] if (_tmdb.is_ready() and len(q.strip()) >= 2) else []
    if resultados and len(q.strip()) >= 3:
        resultados = _tmdb.enrich_movies(resultados, limit=4)
    return jsonify(resultados)


@bp.route('/api/hero/options')
def api_hero_options():
    """Devuelve opciones dinamicas para chips/facetas del buscador avanzado."""
    if not _tmdb.is_ready():
        return jsonify([])
    dimension = request.args.get('dimension', '').strip().lower()
    q = request.args.get('q', '').strip()
    return jsonify(_tmdb.get_dimension_options(dimension, q=q))


@bp.route('/api/hero/search', methods=['POST'])
def api_hero_search():
    """Ejecuta busqueda avanzada por facetas con logica booleana simple (and/or/not)."""
    payload = request.get_json(silent=True) or {}
    selected = payload.get('selected', {})
    logic_mode = str(payload.get('logicMode', 'and')).strip().lower()

    if not _tmdb.is_ready():
        return jsonify({'fallback': True, 'results': []})

    genres     = selected.get('genres', [])
    keywords   = selected.get('keywords', [])
    actors     = selected.get('actors', [])
    directors  = selected.get('directors', [])
    collections = selected.get('collections', [])

    filters = {
        'genres':         genres,
        'keywords':       keywords,
        'actors':         actors,
        'directors':      directors,
        'collections':    collections,
        'genre_ids':      [g.get('id') for g in genres     if isinstance(g, dict) and g.get('id')],
        'keyword_ids':    [k.get('id') for k in keywords   if isinstance(k, dict) and k.get('id')],
        'actor_ids':      [a.get('id') for a in actors     if isinstance(a, dict) and a.get('id')],
        'director_ids':   [d.get('id') for d in directors  if isinstance(d, dict) and d.get('id')],
        'collection_ids': [c.get('id') for c in collections if isinstance(c, dict) and c.get('id')],
    }

    if logic_mode not in ('and', 'or', 'not'):
        logic_mode = 'and'

    return jsonify(_tmdb.hero_search(filters, logic_mode=logic_mode))


@bp.route('/api/movie/<int:movie_id>')
def api_movie_details(movie_id):
    """Entrega detalle liviano de pelicula para hidratar modales bajo demanda."""
    if not _tmdb.is_ready():
        return jsonify({'error': 'TMDB no disponible'}), 503
    try:
        return jsonify(_tmdb.get_movie_details(movie_id, include_related=False))
    except Exception:
        logger.error('api_movie_details falló para movie_id=%s', movie_id, exc_info=True)
        return jsonify({'error': 'No se pudo obtener detalle de la pelicula'}), 502
