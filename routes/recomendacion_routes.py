import re
from concurrent.futures import ThreadPoolExecutor
from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for
from core.logger import get_logger

logger = get_logger(__name__)

from services.tmdb_service import TmdbService
from services.auth_service import AuthService
from core.motor_recomendacion import MotorRecomendacion
from core.motor_explicacion import MotorExplicacion

bp = Blueprint('recomendacion', __name__)

_tmdb:   TmdbService        = None
_motor:  MotorRecomendacion = None
_expl:   MotorExplicacion   = None
_auth:   AuthService        = None

# ---------------------------------------------------------------------------
# Stopwords para queries de semilla (mismas que app.py original)
# ---------------------------------------------------------------------------
_STOPWORDS = {
    'de', 'la', 'el', 'los', 'las', 'del', 'y', 'a', 'en', 'un', 'una', 'the', 'of',
    'and', 'to', 'for', 'con', 'por', 'para', 'es', 'is', 'movie', 'pelicula', 'film',
    'with', 'como', 'con', 'una', 'un', 'the',
}
_GENERIC_TITLE_TERMS = {
    'living', 'story', 'stories', 'chronicles', 'documentary', 'part', 'chapter',
    'life', 'lives', 'unknown', 'new', 'old', 'final', 'rise', 'fall',
}


def register(app, tmdb_service: TmdbService, motor: MotorRecomendacion, explicador: MotorExplicacion, auth_service: AuthService = None):
    """Registra las rutas de recomendacion en la app Flask."""
    global _tmdb, _motor, _expl, _auth
    _tmdb  = tmdb_service
    _motor = motor
    _expl  = explicador
    _auth  = auth_service
    app.register_blueprint(bp)


# ---------------------------------------------------------------------------
# Helpers (extraidos de app.py sin cambios de logica)
# ---------------------------------------------------------------------------

def _tokenize(text):
    raw = str(text or '').lower()
    return [t for t in re.findall(r"[a-z0-9áéíóúñ]+", raw) if len(t) >= 2]


def _validar_historial(historial):
    campos_requeridos = {'id', 'title', 'runtime'}
    validos = []
    for item in historial:
        if isinstance(item, dict) and campos_requeridos.issubset(item.keys()):
            item.setdefault('poster_path', '')
            item.setdefault('genres_list', [])
            item.setdefault('keywords_list', [])
            item.setdefault('cast_list', [])
            item.setdefault('director', '')
            item.setdefault('collection_id', 0)
            item.setdefault('collection_name', '')
            item.setdefault('overview', '')
            item.setdefault('vote_average', 0)
            item.setdefault('progreso', 0)
            item.setdefault('reaccion', 'like')
            validos.append(item)
    return validos


def _completar_campos_reco(items, reaccion='like', val_tiempo=0.0):
    escala = {'double_like': 1.0, 'like': (8.0 / 15.0), 'dislike': 0.0}
    reaccion_label = {'double_like': 'Me encantó', 'like': 'Me gustó', 'dislike': 'No me gustó'}
    out = []
    for item in items:
        rec = dict(item)
        rec.setdefault('genres_list', [])
        rec.setdefault('clasificacion_edad', 0)
        rec.setdefault('release_date', '')
        rec.setdefault('keywords_list', [])
        rec.setdefault('cast_list', [])
        rec.setdefault('director', '')
        rec.setdefault('collection_id', 0)
        rec.setdefault('collection_name', '')
        rec.setdefault('poster_path', '')
        rec.setdefault('runtime', 0)
        rec.setdefault('vote_average', 0)
        rec.setdefault('overview', '')
        rec.setdefault('score_final', round(float(rec.get('vote_average', 0) or 0) / 10.0, 4))
        rec.setdefault('expl_cast', 0.0)
        rec.setdefault('expl_saga', 0.0)
        rec.setdefault('expl_genres', 0.0)
        rec.setdefault('expl_dir', 0.0)
        rec.setdefault('expl_reaccion', 0.0)
        rec.setdefault('expl_tiempo', 0.0)
        rec.setdefault('expl_semantic', 0.0)
        rec.setdefault('expl_intent', 0.0)
        rec.setdefault('expl_quality', 0.0)
        rec.setdefault('val_reaccion', escala.get(reaccion, (8.0 / 15.0)))
        rec.setdefault('val_tiempo', round(val_tiempo, 3))
        rec.setdefault('reaccion_label', reaccion_label.get(reaccion, 'Me gustó'))
        rec.setdefault('shared_cast', [])
        rec.setdefault('shared_genres', [])
        rec.setdefault('same_director', False)
        rec.setdefault('same_saga', False)
        rec.setdefault('saga_name', rec.get('collection_name', ''))
        out.append(rec)
    return out


def _intent_query(movie):
    collection_name = str(movie.get('collection_name') or '').strip()
    if collection_name:
        return collection_name.replace(' - Colección', '').replace(' - Collection', '').strip()

    keywords   = [kw for kw in (movie.get('keywords_list') or []) if str(kw).strip()]
    title_terms = [t for t in _tokenize(movie.get('title', '')) if t not in _STOPWORDS]
    title_terms_strong = [t for t in title_terms if t not in _GENERIC_TITLE_TERMS]

    parts = []
    if keywords:
        parts.extend([str(k) for k in keywords[:2]])
    if title_terms_strong:
        parts.extend(title_terms_strong[:2])
    elif title_terms:
        parts.append(title_terms[0])
        if len(title_terms) > 1:
            parts.append(title_terms[-1])
    return ' '.join(parts).strip()


def _dominant_seed_queries(movie):
    queries = []
    intent = _intent_query(movie)
    if intent:
        queries.append(intent)

    genres     = [str(g).strip() for g in (movie.get('genres_list') or []) if str(g).strip()]
    keywords   = [str(k).strip() for k in (movie.get('keywords_list') or []) if str(k).strip()]
    title_terms = [t for t in _tokenize(movie.get('title', '')) if t not in _STOPWORDS and t not in _GENERIC_TITLE_TERMS]
    primary_genre = genres[0] if genres else ''

    if primary_genre and keywords:
        queries.append(f"{primary_genre} {keywords[0]}")
        queries.append(keywords[0])
    if primary_genre and len(keywords) > 1:
        queries.append(f"{primary_genre} {keywords[1]}")
    if title_terms:
        queries.append(title_terms[-1])
    if primary_genre and 'comedia' in primary_genre.lower():
        queries.append('comedia familiar')
        queries.append('padres familia comedia')
    if primary_genre and 'documental' in primary_genre.lower() and keywords:
        queries.append(' '.join(keywords[:2]))

    unique, seen = [], set()
    for q in queries:
        qn = ' '.join(_tokenize(q))
        if not qn or qn in seen:
            continue
        seen.add(qn)
        unique.append(q)
    return unique[:5]


def _tiene_datos_minimos(item: dict) -> bool:
    """Retorna True si la película tiene datos mínimos para ser recomendada."""
    return bool(
        item.get('poster_path')
        and item.get('overview', '').strip()
        and (item.get('genres_list') or [])
        and int(item.get('runtime') or 0) > 0
    )


def _filtrar_por_edad(items: list) -> list:
    """Elimina peliculas restringidas si el usuario autenticado es menor de edad.

    Usa clasificacion_edad persistida (si existe) o el campo adult de TMDB como fallback.
    """
    if not _auth:
        return items
    usuario = _auth.get_usuario_actual(session)
    if not usuario:
        return items
    # Sin edad registrada: bloquear contenido adulto (+18) por precaución
    if usuario.edad is None:
        return [item for item in items if not item.get('adult', False) and int(item.get('clasificacion_edad') or 0) < 18]
    if usuario.edad >= 18:
        return items
    edad_usuario = usuario.edad

    def _permitida(item):
        # Prioridad: clasificacion_edad persistida en el item
        clasificacion = item.get('clasificacion_edad')
        if clasificacion is not None:
            return edad_usuario >= clasificacion if clasificacion > 0 else True
        # Fallback: campo adult de TMDB
        return not item.get('adult', False)

    return [item for item in items if _permitida(item)]


def _aplicar_scores(items, perfil, reaccion, val_tiempo, descubrimiento=False, diff_opts=None):
    """Calcula y aplica scores a una lista de items usando el motor."""
    for idx, item in enumerate(items):
        if descubrimiento:
            exp = _motor.evaluar_matriz_descubrimiento(item, perfil, val_tiempo=val_tiempo, diff_opts=diff_opts or {})
        else:
            exp = _motor.evaluar_matriz_recomendacion(item, perfil, reaccion=reaccion, val_tiempo=val_tiempo)
        items[idx].update(exp)
    return items


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@bp.route('/api/recomendar', methods=['POST'])
def api_recomendar():
    """Endpoint JSON para React: misma logica que /recomendar pero devuelve JSON."""
    data      = request.get_json(silent=True) or {}
    titulo    = str(data.get('titulo', '')).strip()
    movie_id  = str(data.get('movie_id', '')).strip()
    minutos   = float(data.get('minutos', 0))
    reaccion  = str(data.get('reaccion', 'like'))
    diff_opts = dict(data.get('diff_opts', {})) if isinstance(data.get('diff_opts'), dict) else {}

    if not _tmdb.is_ready():
        return jsonify({'error': 'TMDB no disponible'}), 503

    peli_actual = None
    try:
        if movie_id:
            peli_actual = _tmdb.get_movie_details(int(movie_id))
    except Exception:
        logger.warning('No se pudo obtener detalles de movie_id=%s en api_recomendar', movie_id, exc_info=True)
        peli_actual = None

    if peli_actual is None and titulo:
        found = _tmdb.search_movies(titulo, page=1)
        if found:
            try:
                peli_actual = _tmdb.get_movie_details(int(found[0].get('id')))
            except Exception:
                logger.warning('Fallback a resultado de búsqueda para titulo=%s', titulo, exc_info=True)
                peli_actual = found[0]

    if peli_actual is None:
        return jsonify({'error': 'Pelicula no encontrada'}), 404

    runtime = float(peli_actual.get('runtime') or 0)
    interaccion = {
        'id':              int(peli_actual.get('id', 0)),
        'title':           str(peli_actual.get('title', '')),
        'poster_path':     str(peli_actual.get('poster_path') or ''),
        'genres_list':     list(peli_actual.get('genres_list', [])),
        'keywords_list':   list(peli_actual.get('keywords_list', [])),
        'cast_list':       list(peli_actual.get('cast_list', [])),
        'director':        str(peli_actual.get('director') or ''),
        'collection_id':   int(peli_actual.get('collection_id') or 0),
        'collection_name': str(peli_actual.get('collection_name') or ''),
        'overview':        str(peli_actual.get('overview') or ''),
        'runtime':         runtime,
        'vote_average':    float(peli_actual.get('vote_average') or 0),
        'release_date':    str(peli_actual.get('release_date') or ''),
        'progreso':        round((minutos / max(runtime, 1)) * 100, 1),
        'reaccion':        reaccion,
    }

    # Actualizar historial de sesión
    historial = _validar_historial(session.get('historial', []))
    historial = [i for i in historial if i['id'] != interaccion['id']]
    historial.insert(0, interaccion)
    session['historial'] = historial[:5]

    # Persistir visionado en BD si el usuario está autenticado
    if _auth:
        usuario_bd = _auth.get_usuario_actual(session)
        if usuario_bd and _auth._db:
            interaccion_bd = dict(interaccion)
            interaccion_bd['minutos_vistos'] = int(minutos)
            _auth._db.guardar_visionado(usuario_bd.id, interaccion_bd)

    val_tiempo  = min(1.0, minutos / max(runtime, 1))
    ids_vistos  = [h['id'] for h in historial]

    # -----------------------------------------------------------------------
    # DISLIKE → descubrimiento según dimensiones elegidas por el usuario
    # -----------------------------------------------------------------------
    if reaccion == 'dislike':
        discovery_pool = []
        with ThreadPoolExecutor(max_workers=5) as pool:
            for lista in pool.map(lambda p: _tmdb.get_popular(page=p), range(1, 6)):
                discovery_pool.extend(lista)
        discovery_pool = _tmdb.enrich_movies(discovery_pool, limit=24)
        discovery_pool = [x for x in discovery_pool if int(x.get('id', 0)) not in ids_vistos and _tiene_datos_minimos(x)]
        discovery_pool = _filtrar_por_edad(discovery_pool)
        discovery_scored = _completar_campos_reco(discovery_pool, reaccion='dislike', val_tiempo=val_tiempo)
        discovery_scored = _aplicar_scores(discovery_scored, [interaccion], reaccion, val_tiempo, descubrimiento=True, diff_opts=diff_opts)
        discovery_scored.sort(key=lambda x: float(x.get('score_final', 0.0)), reverse=True)
        lista_recomendados = discovery_scored[:10]
        session['ultima_peli'] = interaccion['title']
        respuesta_dislike = {
            'recomendados':     lista_recomendados,
            'recomendados_sec': [],
            'tipo_sec':         'no_te_gusto',
            'ultima_peli':      interaccion['title'],
            'historial':        session.get('historial', []),
        }
        if _auth:
            usuario_bd = _auth.get_usuario_actual(session)
            if usuario_bd and _auth._db:
                _auth._db.guardar_ultima_consulta(usuario_bd.id, respuesta_dislike)
        return jsonify(respuesta_dislike)

    # -----------------------------------------------------------------------
    # LIKE / DOUBLE_LIKE
    # -----------------------------------------------------------------------
    # Sección 1: 10 similares directos a la película actual
    # Pool: recomendaciones TMDB + películas de misma saga + búsquedas por keywords
    similares_pool = []
    if isinstance(peli_actual, dict):
        similares_pool.extend(peli_actual.get('recommendations', []))
        similares_pool.extend(peli_actual.get('similar', []))
    similares_pool.extend(_tmdb.search_movies_many(_dominant_seed_queries(interaccion), pages=(1, 2)))
    dedup, seen_s = [], set()
    for item in similares_pool:
        mid = int(item.get('id', 0) or 0)
        if not mid or mid in seen_s:
            continue
        seen_s.add(mid)
        dedup.append(item)
    similares_pool = _tmdb.enrich_movies(dedup, limit=20)
    similares_pool = [x for x in similares_pool if int(x.get('id', 0)) not in ids_vistos and _tiene_datos_minimos(x)]
    similares_pool = _filtrar_por_edad(similares_pool)
    sim_scored = _completar_campos_reco(similares_pool, reaccion=reaccion, val_tiempo=val_tiempo)
    sim_scored = _aplicar_scores(sim_scored, [interaccion], reaccion, val_tiempo)
    sim_scored.sort(key=lambda x: float(x.get('score_final', 0.0)), reverse=True)
    lista_recomendados = sim_scored[:10]

    ids_primarios = {int(x.get('id', 0)) for x in lista_recomendados if x.get('id')}

    # Sección 2: "fuera de dimensión"
    # Buscar directamente por keywords de la película base en TMDB.
    # Filtrar las que tengan el género PRINCIPAL de la base.
    # Ordenar por similitud semántica pura (keywords + overview), sin peso de calificación.
    genero_principal = interaccion['genres_list'][0] if interaccion['genres_list'] else ''
    kws_base = [str(kw).strip() for kw in (interaccion['keywords_list'] or []) if str(kw).strip()]

    fuera_pool = []
    # Búsqueda directa por cada keyword
    fuera_pool.extend(_tmdb.search_movies_many(kws_base[:6], pages=(1, 2)))

    dedup_f, seen_f = [], set()
    for item in fuera_pool:
        mid = int(item.get('id', 0) or 0)
        if not mid or mid in seen_f:
            continue
        seen_f.add(mid)
        dedup_f.append(item)
    fuera_pool = _tmdb.enrich_movies(dedup_f, limit=40)

    # Filtrar: excluir vistos, ya recomendados, sin datos mínimos,
    # los que tengan el género PRINCIPAL de la base, y cortometrajes/series cortas (<60 min)
    fuera_pool = [
        x for x in fuera_pool
        if int(x.get('id', 0)) not in ids_vistos
        and int(x.get('id', 0)) not in ids_primarios
        and _tiene_datos_minimos(x)
        and int(x.get('runtime') or 0) >= 30
        and (not genero_principal or genero_principal not in (x.get('genres_list') or []))
    ]
    fuera_pool = _filtrar_por_edad(fuera_pool)
    fuera_scored = _completar_campos_reco(fuera_pool, reaccion=reaccion, val_tiempo=val_tiempo)
    fuera_scored = _aplicar_scores(fuera_scored, [interaccion], reaccion, val_tiempo)
    # Pre-calcular cuántas keywords de la base aparecen en cada candidata (para desempate)
    kws_base_set = set(str(kw).lower().strip() for kw in kws_base)
    for x in fuera_scored:
        kws_cand = set(str(kw).lower().strip() for kw in (x.get('keywords_list') or []))
        x['_kw_matches'] = len(kws_base_set & kws_cand)
    # Ordenar: primero por keywords coincidentes, luego por similitud semántica
    fuera_scored.sort(
        key=lambda x: (x.get('_kw_matches', 0), float(x.get('expl_semantic', 0.0))),
        reverse=True,
    )
    sec_list = fuera_scored[:10]

    tipo_sec = 'te_encanto' if reaccion == 'double_like' else 'te_gusto'
    session['ultima_peli'] = interaccion['title']

    respuesta = {
        'recomendados':     lista_recomendados,
        'recomendados_sec': sec_list,
        'tipo_sec':         tipo_sec,
        'ultima_peli':      interaccion['title'],
        'historial':        session.get('historial', []),
    }

    # Persistir última consulta en BD por usuario
    if _auth:
        usuario_bd = _auth.get_usuario_actual(session)
        if usuario_bd and _auth._db:
            _auth._db.guardar_ultima_consulta(usuario_bd.id, respuesta)

    return jsonify(respuesta)


@bp.route('/recomendar', methods=['POST'])
def recomendar():
    """Orquesta el flujo completo: registra interaccion, rankea y renderiza recomendaciones."""
    titulo   = request.form.get('titulo', '').strip()
    movie_id = request.form.get('movie_id', '').strip()
    minutos  = float(request.form.get('minutos', 0))
    reaccion = request.form.get('reaccion', 'like')

    if not _tmdb.is_ready():
        return redirect(url_for('index'))

    peli_actual = None
    try:
        if movie_id:
            peli_actual = _tmdb.get_movie_details(int(movie_id))
    except Exception:
        logger.warning('No se pudo obtener detalles de movie_id=%s en recomendar', movie_id, exc_info=True)
        peli_actual = None

    if peli_actual is None and titulo:
        found = _tmdb.search_movies(titulo, page=1)
        if found:
            try:
                peli_actual = _tmdb.get_movie_details(int(found[0].get('id')))
            except Exception:
                logger.warning('Fallback a resultado de búsqueda para titulo=%s', titulo, exc_info=True)
                peli_actual = found[0]

    if peli_actual is None:
        return redirect(url_for('index'))

    runtime = float(peli_actual.get('runtime') or 0)
    interaccion = {
        'id':              int(peli_actual.get('id', 0)),
        'title':           str(peli_actual.get('title', '')),
        'poster_path':     str(peli_actual.get('poster_path') or ''),
        'genres_list':     list(peli_actual.get('genres_list', [])),
        'keywords_list':   list(peli_actual.get('keywords_list', [])),
        'cast_list':       list(peli_actual.get('cast_list', [])),
        'director':        str(peli_actual.get('director') or ''),
        'collection_id':   int(peli_actual.get('collection_id') or 0),
        'collection_name': str(peli_actual.get('collection_name') or ''),
        'overview':        str(peli_actual.get('overview') or ''),
        'runtime':         runtime,
        'vote_average':    float(peli_actual.get('vote_average') or 0),
        'release_date':    str(peli_actual.get('release_date') or ''),
        'progreso':        round((minutos / max(runtime, 1)) * 100, 1),
        'reaccion':        reaccion,
    }

    historial = _validar_historial(session.get('historial', []))
    historial = [i for i in historial if i['id'] != interaccion['id']]
    historial.insert(0, interaccion)
    session['historial'] = historial[:5]

    perfil      = _validar_historial(session.get('historial', []))[:5]
    val_tiempo  = min(1.0, minutos / max(runtime, 1))
    ids_vistos  = [h['id'] for h in perfil]

    # --- Seccion principal: recomendaciones desde historial ---
    recs = _tmdb.recommend_from_history(perfil, limit=20)
    recs = _tmdb.enrich_movies(recs, limit=14)
    recs = [r for r in recs if int(r.get('id', 0)) not in ids_vistos]
    recs = _filtrar_por_edad(recs)

    recs_scored = _completar_campos_reco(recs, reaccion=reaccion, val_tiempo=val_tiempo)
    recs_scored = _aplicar_scores(recs_scored, perfil, reaccion, val_tiempo)
    recs_scored.sort(key=lambda x: float(x.get('score_final', 0.0)), reverse=True)
    lista_recomendados = recs_scored[:10]

    ids_primarios = {int(x.get('id', 0)) for x in lista_recomendados if x.get('id')}

    # --- Seccion secundaria: depth/exploration segun reaccion ---
    if reaccion in ('like', 'double_like'):
        latest_pool = []
        if isinstance(peli_actual, dict):
            latest_pool.extend(peli_actual.get('recommendations', []))
            latest_pool.extend(peli_actual.get('similar', []))

        for q in _dominant_seed_queries(interaccion):
            for page in range(1, 3):
                latest_pool.extend(_tmdb.search_movies(q, page=page))

        dedup, seen_l = [], set()
        for item in latest_pool:
            mid = int(item.get('id', 0) or 0)
            if not mid or mid in seen_l:
                continue
            seen_l.add(mid)
            dedup.append(item)

        latest_pool = _tmdb.enrich_movies(dedup, limit=20)
        latest_pool = [x for x in latest_pool if int(x.get('id', 0)) not in ids_vistos]
        latest_pool = _filtrar_por_edad(latest_pool)

        sec_scored = _completar_campos_reco(latest_pool, reaccion=reaccion, val_tiempo=val_tiempo)
        sec_scored = _aplicar_scores(sec_scored, [interaccion], reaccion, val_tiempo)
        sec_scored.sort(key=lambda x: float(x.get('score_final', 0.0)), reverse=True)
        sec_list = sec_scored[:10]

        if len(sec_list) < 10:
            existing = {int(x.get('id', 0)) for x in sec_list if x.get('id')}
            for item in recs_scored:
                mid = int(item.get('id', 0) or 0)
                if not mid or mid in existing or mid in ids_primarios:
                    continue
                sec_list.append(item)
                existing.add(mid)
                if len(sec_list) >= 10:
                    break
    else:
        discovery_pool = []
        for page in range(1, 6):
            discovery_pool.extend(_tmdb.get_popular(page=page))

        discovery_pool = _tmdb.enrich_movies(discovery_pool, limit=24)
        discovery_pool = [
            x for x in discovery_pool
            if int(x.get('id', 0)) not in ids_vistos and int(x.get('id', 0)) not in ids_primarios
        ]
        discovery_pool = _filtrar_por_edad(discovery_pool)

        discovery_scored = _completar_campos_reco(discovery_pool, reaccion='dislike', val_tiempo=val_tiempo)
        discovery_scored = _aplicar_scores(discovery_scored, perfil, reaccion, val_tiempo, descubrimiento=True)
        discovery_scored = [
            x for x in discovery_scored
            if float(x.get('expl_genres', 0.0)) >= 0.18 and float(x.get('expl_cast', 0.0)) >= 0.15
        ]
        discovery_scored.sort(key=lambda x: float(x.get('score_final', 0.0)), reverse=True)
        sec_list = discovery_scored[:10]

    tipo_sec = 'no_te_gusto' if reaccion == 'dislike' else ('te_encanto' if reaccion == 'double_like' else 'te_gusto')
    session['ultima_peli'] = interaccion['title']

    usuario_actual = _auth.get_usuario_actual(session) if _auth else None
    return render_template(
        'index.html',
        top_10=_tmdb.get_popular(page=1)[:10],
        recomendados=lista_recomendados,
        recomendados_sec=sec_list,
        tipo_sec=tipo_sec,
        historial=session.get('historial', []),
        ultima_peli=interaccion['title'],
        usuario=usuario_actual,
    )


# ---------------------------------------------------------------------------
# API IR Metrics
# ---------------------------------------------------------------------------

@bp.route('/api/recomendacion/ir-metrics', methods=['GET'])
def api_ir_metrics():
    """Devuelve metricas IR del historial de sesion actual.

    Calcula un score promedio por tecnica sobre las peliculas del historial
    para diagnostico y visualizacion academica.

    Respuesta:
    {
      "n_historial": int,
      "tecnicas": {
        "jaccard":     float,   -- Jaccard simple (overviews/titulos)
        "jaccard_idf": float,   -- Jaccard ponderado con IDF (cast+generos)
        "bm25":        float,   -- BM25/intent (similitud tematica token-based)
        "semantica":   float,   -- Similitud semantica combinada
        "intent":      float    -- Similitud de intencion tematica
      },
      "idf_terms": {campo: {term: idf_value}},  -- IDF calculado desde historial
      "historial_titles": [str]
    }
    """
    from core.gestor_dimensiones import GestorDimensiones

    historial = _validar_historial(session.get('historial', []))
    n = len(historial)

    if n == 0:
        return jsonify({
            'n_historial': 0,
            'tecnicas': {'jaccard': 0.0, 'jaccard_idf': 0.0, 'bm25': 0.0, 'semantica': 0.0, 'intent': 0.0},
            'idf_terms': {},
            'historial_titles': [],
        })

    dim = GestorDimensiones()
    idf_generos  = dim.idf_from_history(historial, 'genres_list')
    idf_keywords = dim.idf_from_history(historial, 'keywords_list')
    idf_cast     = dim.idf_from_history(historial, 'cast_list')

    # Calcula similitudes entre pares del historial para estimar activacion de cada tecnica
    jaccard_vals, jaccard_idf_vals, semantica_vals, intent_vals = [], [], [], []

    for i in range(n):
        for j in range(i + 1, n):
            a, b = historial[i], historial[j]

            ov_a = dim.tokenize(a.get('overview', ''))
            ov_b = dim.tokenize(b.get('overview', ''))
            jaccard_vals.append(dim.jaccard(ov_a, ov_b))

            jaccard_idf_vals.append(
                0.5 * dim.weighted_jaccard(a.get('cast_list', []), b.get('cast_list', []), idf=idf_cast)
                + 0.5 * dim.weighted_jaccard(a.get('genres_list', []), b.get('genres_list', []), idf=idf_generos)
            )

            kw_sim = dim.weighted_jaccard(a.get('keywords_list', []), b.get('keywords_list', []), idf=idf_keywords)
            ttl_sim = dim.jaccard(dim.tokenize(a.get('title', '')), dim.tokenize(b.get('title', '')))
            semantica_vals.append(min(1.0, 0.45 * kw_sim + 0.35 * dim.jaccard(ov_a, ov_b) + 0.20 * ttl_sim))

            intent_vals.append(dim.intent_similarity(a, b))

    def _avg(lst):
        return round(sum(lst) / len(lst), 4) if lst else 0.0

    avg_jaccard     = _avg(jaccard_vals)
    avg_jaccard_idf = _avg(jaccard_idf_vals)
    avg_semantica   = _avg(semantica_vals)
    avg_intent      = _avg(intent_vals)

    # IDF terms — top 10 por campo para visualizacion
    def _top_idf(idf_dict, k=10):
        return dict(sorted(idf_dict.items(), key=lambda x: x[1], reverse=True)[:k])

    return jsonify({
        'n_historial': n,
        'tecnicas': {
            'jaccard':     avg_jaccard,
            'jaccard_idf': avg_jaccard_idf,
            'bm25':        avg_intent,   # BM25 approximado via intent token-based
            'semantica':   avg_semantica,
            'intent':      avg_intent,
        },
        'idf_terms': {
            'generos':  _top_idf(idf_generos),
            'keywords': _top_idf(idf_keywords),
            'cast':     _top_idf(idf_cast),
        },
        'historial_titles': [h.get('title', '') for h in historial],
    })
