import os
import math
from collections import Counter
from datetime import datetime, timedelta, timezone

import requests

from services.db_service import DatabaseService
from core.logger import get_logger

logger = get_logger(__name__)


class TmdbService:
    def __init__(self, db_service: DatabaseService = None):
        """Inicializa cliente TMDB. La cache de BD se delega a DatabaseService."""
        self.api_key = os.getenv('TMDB_API_KEY', '').strip()
        self.base_url = os.getenv('TMDB_BASE_URL', 'https://api.themoviedb.org/3').strip()
        self.language = os.getenv('TMDB_LANGUAGE', 'es-MX').strip()
        self.image_base = os.getenv('TMDB_IMAGE_BASE', 'https://image.tmdb.org/t/p/w500').strip()
        self.enabled = bool(self.api_key)
        self.request_timeout = float(os.getenv('TMDB_TIMEOUT_SECONDS', '10').strip() or 10)
        self._db = db_service
        self._genre_map_cache = {}
        self._genre_map_expires_at = datetime.now(timezone.utc)
        self._http = requests.Session()

    def _get_genre_map(self):
        """Obtiene y cachea el mapa id->nombre de generos de TMDB."""
        now = datetime.now(timezone.utc)
        if self._genre_map_cache and now < self._genre_map_expires_at:
            return self._genre_map_cache

        data = self._request('/genre/movie/list', {}, ttl_seconds=86400)
        genre_map = {}
        for g in data.get('genres', []):
            try:
                gid = int(g.get('id') or 0)
            except Exception:
                logger.debug('No se pudo parsear genre id: %s', g)
                gid = 0
            name = str(g.get('name') or '').strip()
            if gid and name:
                genre_map[gid] = name

        if genre_map:
            self._genre_map_cache = genre_map
            self._genre_map_expires_at = now + timedelta(hours=12)

        return self._genre_map_cache

    def _request(self, path, params=None, ttl_seconds=3600):
        """Ejecuta request a TMDB con cache por llave (ruta+params+idioma)."""
        if not self.enabled:
            return {}

        params = dict(params or {})
        params['api_key'] = self.api_key
        params.setdefault('language', self.language)

        if self._db:
            cache_key = self._db.cache_key(path, params)
            cached = self._db.cache_get(cache_key)
            if cached is not None:
                return cached

        url = f"{self.base_url}{path}"
        response = self._http.get(url, params=params, timeout=self.request_timeout)
        response.raise_for_status()
        data = response.json()

        if self._db:
            self._db.cache_set(cache_key, data, ttl_seconds)

        return data

    def is_ready(self):
        return self.enabled

    def map_movie(self, movie):
        """Normaliza TMDB a la estructura interna usada por la app."""
        genre_names = []
        if isinstance(movie.get('genre_ids'), list):
            genre_map = self._get_genre_map()
            for g in movie.get('genre_ids', []):
                try:
                    gid = int(g)
                except Exception:
                    logger.debug('No se pudo parsear genre_id=%s en movie_id=%s', g, movie.get('id'))
                    continue
                genre_names.append(genre_map.get(gid, str(gid)))
        elif isinstance(movie.get('genres'), list):
            genre_names = [g.get('name', '') for g in movie.get('genres', []) if isinstance(g, dict)]

        return {
            'id': int(movie.get('id', 0) or 0),
            'title': movie.get('title') or movie.get('name') or '',
            'genres_list': genre_names,
            'keywords_list': [],
            'cast_list': [],
            'director': '',
            'collection_id': 0,
            'collection_name': '',
            'poster_path': movie.get('poster_path') or '',
            'runtime': float(movie.get('runtime') or 0),
            'vote_average': float(movie.get('vote_average') or 0),
            'overview': movie.get('overview', ''),
            'release_date': movie.get('release_date', ''),
            'clasificacion_edad': 18 if movie.get('adult', False) else 0,
            'adult': bool(movie.get('adult', False)),
        }

    @staticmethod
    def _tokenize_text(text):
        raw = str(text or '').lower()
        return [t for t in __import__('re').findall(r"[a-z0-9áéíóúñ]+", raw) if len(t) >= 2]

    @staticmethod
    def _normalize_scores(score_dict):
        if not score_dict:
            return {}
        vals = list(score_dict.values())
        mn = min(vals)
        mx = max(vals)
        if mx - mn < 1e-12:
            return {k: 0.0 for k in score_dict.keys()}
        return {k: (v - mn) / (mx - mn) for k, v in score_dict.items()}

    def _build_query_terms_from_history(self, history):
        terms = []
        for h in history:
            title = h.get('title', '')
            genres = h.get('genres_list', []) or []
            keywords = h.get('keywords_list', []) or []
            overview = h.get('overview', '')
            terms.extend(self._tokenize_text(title))
            terms.extend(self._tokenize_text(overview))
            for g in genres:
                terms.extend(self._tokenize_text(g))
            for kw in keywords:
                terms.extend(self._tokenize_text(kw))
        return terms

    def _candidate_terms(self, movie):
        terms = []
        terms.extend(self._tokenize_text(movie.get('title', '')))
        terms.extend(self._tokenize_text(movie.get('overview', '')))
        for g in movie.get('genres_list', []) or []:
            terms.extend(self._tokenize_text(g))
        for kw in movie.get('keywords_list', []) or []:
            terms.extend(self._tokenize_text(kw))
        return terms

    @staticmethod
    def _derive_keywords_from_text(title, overview, max_terms=8):
        stop = {
            'de', 'la', 'el', 'los', 'las', 'del', 'y', 'a', 'en', 'un', 'una', 'the', 'of',
            'and', 'to', 'for', 'con', 'por', 'para', 'es', 'is', 'this', 'that', 'movie',
            'film', 'from', 'with', 'como', 'sobre', 'into', 'its', 'their', 'his', 'her'
        }
        tokens = []
        for t in __import__('re').findall(r"[a-z0-9áéíóúñ]+", f"{title or ''} {overview or ''}".lower()):
            if len(t) < 4 or t in stop:
                continue
            tokens.append(t)

        if not tokens:
            return []

        freq = Counter(tokens)
        ordered = [w for w, _ in freq.most_common(max_terms)]
        return ordered

    def _bm25_scores(self, query_terms, docs_terms, k1=1.5, b=0.75):
        """Calcula score BM25 por documento para una consulta tokenizada."""
        if not query_terms or not docs_terms:
            return {doc_id: 0.0 for doc_id in docs_terms.keys()}

        N = len(docs_terms)
        q_counter = Counter(query_terms)
        df = Counter()
        doc_lens = {}
        tf_docs = {}

        for doc_id, terms in docs_terms.items():
            tf = Counter(terms)
            tf_docs[doc_id] = tf
            doc_lens[doc_id] = sum(tf.values())
            for t in set(terms):
                df[t] += 1

        avgdl = sum(doc_lens.values()) / max(N, 1)
        if avgdl <= 0:
            avgdl = 1.0

        scores = {}
        for doc_id, tf in tf_docs.items():
            dl = doc_lens.get(doc_id, 1)
            score = 0.0
            for t, qf in q_counter.items():
                dfi = df.get(t, 0)
                if dfi == 0:
                    continue
                idf = math.log(1 + ((N - dfi + 0.5) / (dfi + 0.5)))
                f = tf.get(t, 0)
                if f <= 0:
                    continue
                denom = f + k1 * (1 - b + b * (dl / avgdl))
                score += idf * ((f * (k1 + 1)) / max(denom, 1e-9)) * (1 + math.log(1 + qf))
            scores[doc_id] = score

        return scores

    def search_movies(self, query, page=1):
        """Busca peliculas por texto libre en TMDB."""
        data = self._request('/search/movie', {
            'query': query,
            'page': page,
            'include_adult': 'false'
        }, ttl_seconds=900)
        return [self.map_movie(m) for m in data.get('results', [])]

    def get_popular(self, page=1):
        """Obtiene listado de peliculas populares."""
        data = self._request('/movie/popular', {'page': page}, ttl_seconds=1800)
        return [self.map_movie(m) for m in data.get('results', [])]

    # Mapeo de certificaciones TMDB a edad mínima requerida
    _CERT_TO_AGE = {
        # US (MPAA)
        'G': 0, 'PG': 7, 'PG-13': 13, 'R': 16, 'NC-17': 18, 'NR': 0,
        # ES (España)
        'APTA': 0, 'A': 0, '7': 7, '12': 12, '13': 13, '16': 16, '18': 18,
        # MX
        'AA': 0, 'A (MX)': 0, 'B': 12, 'B-15': 15, 'C': 18, 'D': 18,
        # DE (Alemania - FSK)
        '0': 0, '6': 6, '12 (DE)': 12, '16 (DE)': 16, '18 (DE)': 18,
        # GB (Reino Unido - BBFC)
        'U': 0, 'PG (GB)': 7, '12A': 12, '15': 15, '18 (GB)': 18, 'R18': 18,
        # BR (Brasil)
        'L': 0, '10': 10, '12 (BR)': 12, '14': 14, '16 (BR)': 16, '18 (BR)': 18,
    }

    @classmethod
    def _extract_certification_age(cls, release_dates_data):
        """Extrae la clasificación de edad real a partir de release_dates de TMDB.

        Prioriza certificaciones de US, luego ES, MX, GB, DE, BR y finalmente cualquier país.
        """
        if not isinstance(release_dates_data, dict):
            return None
        results = release_dates_data.get('results', [])
        if not results:
            return None

        # Orden de preferencia de país
        priority_countries = ['US', 'ES', 'MX', 'GB', 'DE', 'BR']
        by_country = {r.get('iso_3166_1', ''): r.get('release_dates', []) for r in results if isinstance(r, dict)}

        for country in priority_countries:
            releases = by_country.get(country, [])
            for rel in releases:
                cert = str(rel.get('certification', '')).strip()
                if not cert:
                    continue
                # Buscar directo en el mapa
                if cert in cls._CERT_TO_AGE:
                    return cls._CERT_TO_AGE[cert]
                # Intentar interpretar como número
                try:
                    num = int(cert)
                    if 0 <= num <= 21:
                        return num
                except ValueError:
                    pass

        # Fallback: cualquier país con certificación numérica o conocida
        for releases in by_country.values():
            for rel in releases:
                cert = str(rel.get('certification', '')).strip()
                if not cert:
                    continue
                if cert in cls._CERT_TO_AGE:
                    return cls._CERT_TO_AGE[cert]
                try:
                    num = int(cert)
                    if 0 <= num <= 21:
                        return num
                except ValueError:
                    pass

        return None

    def get_movie_details(self, movie_id, include_related=True):
        """Trae detalle completo de una pelicula y aplica fallbacks de idioma/metadatos."""
        append_parts = ['credits', 'keywords', 'release_dates']
        if include_related:
            append_parts.extend(['recommendations', 'similar'])

        data = self._request(
            f'/movie/{movie_id}',
            {'append_to_response': ','.join(append_parts)},
            ttl_seconds=3600
        )
        base = self.map_movie(data)
        credits = data.get('credits', {}) if isinstance(data, dict) else {}
        cast = credits.get('cast', []) if isinstance(credits, dict) else []
        crew = credits.get('crew', []) if isinstance(credits, dict) else []
        director = ''
        for person in crew:
            if person.get('job') == 'Director':
                director = person.get('name', '')
                break

        base['cast_list'] = [c.get('name', '') for c in cast[:6] if c.get('name')]
        base['director'] = director
        base['genres_list'] = [g.get('name', '') for g in data.get('genres', []) if g.get('name')]
        coll = data.get('belongs_to_collection') or {}
        if isinstance(coll, dict):
            base['collection_id'] = int(coll.get('id') or 0)
            base['collection_name'] = coll.get('name', '') or ''

        keyword_items = []
        kw_obj = data.get('keywords', {})
        if isinstance(kw_obj, dict):
            keyword_items = kw_obj.get('keywords', [])
        base['keywords_list'] = [k.get('name', '') for k in keyword_items if k.get('name')]

        # Fallback: muchos titulos en es-MX vienen sin overview/keywords.
        needs_overview = not str(base.get('overview') or '').strip()
        needs_keywords = len(base.get('keywords_list', []) or []) == 0
        if needs_overview or needs_keywords:
            try:
                data_en = self._request(
                    f'/movie/{movie_id}',
                    {
                        'append_to_response': 'credits,keywords',
                        'language': 'en-US'
                    },
                    ttl_seconds=3600
                )
                if needs_overview:
                    ov_en = str(data_en.get('overview') or '').strip()
                    if ov_en:
                        base['overview'] = ov_en
                    elif str(data_en.get('tagline') or '').strip():
                        base['overview'] = str(data_en.get('tagline') or '').strip()

                if needs_keywords:
                    kw_en_obj = data_en.get('keywords', {})
                    kw_en_items = kw_en_obj.get('keywords', []) if isinstance(kw_en_obj, dict) else []
                    kws_en = [k.get('name', '') for k in kw_en_items if k.get('name')]
                    if kws_en:
                        base['keywords_list'] = kws_en
            except Exception:
                logger.debug('Fallo al obtener datos en inglés para movie_id=%s — usando datos en español', base.get('id'), exc_info=True)

        if not str(base.get('overview') or '').strip():
            fallback_overview = str(data.get('tagline') or '').strip()
            if fallback_overview:
                base['overview'] = fallback_overview

        if len(base.get('keywords_list', []) or []) == 0:
            base['keywords_list'] = self._derive_keywords_from_text(
                base.get('title', ''), base.get('overview', ''), max_terms=8
            )

        rec = data.get('recommendations', {}).get('results', []) if isinstance(data.get('recommendations'), dict) else []
        sim = data.get('similar', {}).get('results', []) if isinstance(data.get('similar'), dict) else []
        base['recommendations'] = [self.map_movie(m) for m in rec] if include_related else []
        base['similar'] = [self.map_movie(m) for m in sim] if include_related else []

        # --- Clasificacion de edad (usando certificaciones reales) ---
        adult = bool(data.get('adult', False))
        cert_age = self._extract_certification_age(data.get('release_dates'))
        if cert_age is not None:
            clasificacion_edad = cert_age
        else:
            clasificacion_edad = 18 if adult else 0
        base['adult'] = adult
        base['clasificacion_edad'] = clasificacion_edad

        if self._db:
            mid = int(base.get('id') or 0)
            titulo = str(base.get('title') or '')
            if mid:
                self._db.upsert_pelicula_clasificacion(mid, titulo, clasificacion_edad, adult)

        return base

    def get_dimension_options(self, dimension, q=''):
        """Resuelve opciones para el buscador avanzado por dimension (genero, actor, etc.)."""
        q = (q or '').strip()
        if dimension == 'genre':
            data = self._request('/genre/movie/list', {}, ttl_seconds=86400)
            options = [{'id': g.get('id'), 'name': g.get('name')} for g in data.get('genres', [])]
            if q:
                ql = q.lower()
                options = [o for o in options if ql in str(o.get('name', '')).lower()]
            return options[:60]

        if dimension == 'keyword':
            if len(q) < 2:
                return []
            data = self._request('/search/keyword', {'query': q, 'page': 1}, ttl_seconds=3600)
            return [{'id': r.get('id'), 'name': r.get('name')} for r in data.get('results', [])[:25]]

        if dimension in ('actor', 'director'):
            if len(q) < 2:
                return []
            data = self._request('/search/person', {'query': q, 'page': 1, 'include_adult': 'false'}, ttl_seconds=1800)
            results = []
            for r in data.get('results', []):
                dept = (r.get('known_for_department') or '').lower()
                if dimension == 'actor' and dept not in ('acting', ''):
                    continue
                if dimension == 'director' and dept not in ('directing', ''):
                    continue
                results.append({'id': r.get('id'), 'name': r.get('name')})
                if len(results) >= 25:
                    break
            return results

        if dimension == 'collection':
            if len(q) < 2:
                return []
            data = self._request('/search/collection', {'query': q, 'page': 1}, ttl_seconds=3600)
            direct = [{'id': r.get('id'), 'name': r.get('name')} for r in data.get('results', [])[:25]]
            if not direct:
                data_en = self._request(
                    '/search/collection',
                    {'query': q, 'page': 1, 'language': 'en-US'},
                    ttl_seconds=3600,
                )
                direct = [{'id': r.get('id'), 'name': r.get('name')} for r in data_en.get('results', [])[:25]]
            if direct:
                return direct

            # Fallback: buscar peliculas y recuperar su coleccion
            movie_hits = self.search_movies(q, page=1)[:12]
            if not movie_hits:
                data_movies_en = self._request(
                    '/search/movie',
                    {'query': q, 'page': 1, 'language': 'en-US', 'include_adult': False},
                    ttl_seconds=3600,
                )
                movie_hits = []
                for m in data_movies_en.get('results', [])[:12]:
                    movie_hits.append({
                        'id': int(m.get('id') or 0),
                        'title': m.get('title') or m.get('name') or 'Sin titulo',
                        'year': (m.get('release_date', '') or '')[:4],
                        'poster': self._poster_url(m.get('poster_path')),
                        'rating': float(m.get('vote_average', 0.0) or 0.0),
                        'overview': m.get('overview', '') or '',
                        'genres': '',
                    })
            collections = {}
            for m in movie_hits:
                mid = int(m.get('id') or 0)
                if not mid:
                    continue
                try:
                    d = self.get_movie_details(mid)
                    cid = int(d.get('collection_id') or 0)
                    cname = d.get('collection_name', '')
                    if cid and cname:
                        collections[cid] = cname
                except Exception:
                    logger.debug('No se pudo obtener detalles para movie_id=%s en búsqueda de colecciones', mid, exc_info=True)
                    continue

            return [{'id': cid, 'name': name} for cid, name in collections.items()][:25]

        return []

    def _collection_movie_ids(self, collection_ids):
        ids = set()
        for cid in collection_ids:
            data = self._request(f'/collection/{cid}', {}, ttl_seconds=3600)
            for p in data.get('parts', []):
                mid = p.get('id')
                if mid:
                    ids.add(int(mid))
        return ids

    def _collection_movies(self, collection_ids):
        movies = []
        seen = set()
        for cid in collection_ids:
            data = self._request(f'/collection/{cid}', {}, ttl_seconds=3600)
            parts = data.get('parts', [])
            for p in parts:
                mid = int(p.get('id') or 0)
                if not mid or mid in seen:
                    continue
                seen.add(mid)
                movies.append(self.map_movie(p))

        movies.sort(key=lambda m: m.get('release_date') or '', reverse=True)
        return movies

    @staticmethod
    def _dedupe_movies(movies):
        out = []
        seen = set()
        for m in movies:
            mid = int(m.get('id', 0) or 0)
            if not mid or mid in seen:
                continue
            seen.add(mid)
            out.append(m)
        return out

    def _expand_movie_details(self, movies, limit=20):
        """Enriquece listas de peliculas con detalle adicional de forma acotada por limite."""
        if not movies:
            return []

        expanded = []
        for idx, movie in enumerate(movies):
            item = dict(movie)
            need_details = (
                not item.get('cast_list') or
                not item.get('director') or
                float(item.get('runtime') or 0) <= 0
            )

            if need_details and idx < limit:
                mid = int(item.get('id', 0) or 0)
                if mid:
                    try:
                        details = self.get_movie_details(mid, include_related=False)
                        item['genres_list'] = details.get('genres_list', item.get('genres_list', []))
                        item['keywords_list'] = details.get('keywords_list', item.get('keywords_list', []))
                        item['overview'] = details.get('overview', item.get('overview', ''))
                        item['cast_list'] = details.get('cast_list', item.get('cast_list', []))
                        item['director'] = details.get('director', item.get('director', ''))
                        item['runtime'] = details.get('runtime', item.get('runtime', 0))
                        item['collection_id'] = details.get('collection_id', item.get('collection_id', 0))
                        item['collection_name'] = details.get('collection_name', item.get('collection_name', ''))
                        item['clasificacion_edad'] = details.get('clasificacion_edad', item.get('clasificacion_edad', 0))
                        item['adult'] = details.get('adult', item.get('adult', False))
                        item['release_date'] = details.get('release_date', item.get('release_date', ''))
                    except Exception:
                        logger.warning('No se pudo enriquecer movie_id=%s — se usarán datos parciales', mid, exc_info=True)

            expanded.append(item)

        return expanded

    def enrich_movies(self, movies, limit=20):
        return self._expand_movie_details(movies, limit=limit)

    def discover_with_filters(self, filters, page=1, mode='and'):
        """Construye busqueda por filtros usando discover de TMDB y logica and/or."""
        filters = filters or {}
        mode = str(mode or 'and').strip().lower()

        genre_ids = [str(x) for x in filters.get('genre_ids', []) if x]
        keyword_ids = [str(x) for x in filters.get('keyword_ids', []) if x]
        actor_ids = [str(x) for x in filters.get('actor_ids', []) if x]
        director_ids = [str(x) for x in filters.get('director_ids', []) if x]
        collection_ids = [int(x) for x in filters.get('collection_ids', []) if x]

        has_discover_filters = bool(genre_ids or keyword_ids or actor_ids or director_ids)

        if collection_ids and not has_discover_filters:
            return self._collection_movies(collection_ids)

        params = {
            'page': page,
            'include_adult': 'false',
            'sort_by': 'popularity.desc'
        }

        if genre_ids:
            sep = '|' if mode == 'or' else ','
            params['with_genres'] = sep.join(genre_ids)
        if keyword_ids:
            sep = '|' if mode == 'or' else ','
            params['with_keywords'] = sep.join(keyword_ids)
        if actor_ids:
            params['with_cast'] = '|'.join(actor_ids)
        if director_ids:
            params['with_crew'] = '|'.join(director_ids)

        results = []
        for p in range(1, 6):
            params['page'] = p
            data = self._request('/discover/movie', params, ttl_seconds=900)
            chunk = [self.map_movie(m) for m in data.get('results', [])]
            results.extend(chunk)
            if not chunk:
                break

        if collection_ids:
            allowed = self._collection_movie_ids(collection_ids)
            if allowed:
                results = [m for m in results if int(m.get('id', 0)) in allowed]

        return self._dedupe_movies(results)

    def _or_search(self, filters):
        groups = []
        if filters.get('genre_ids'):
            groups.append({'genre_ids': filters.get('genre_ids', [])})
        if filters.get('keyword_ids'):
            groups.append({'keyword_ids': filters.get('keyword_ids', [])})
        if filters.get('actor_ids'):
            groups.append({'actor_ids': filters.get('actor_ids', [])})
        if filters.get('director_ids'):
            groups.append({'director_ids': filters.get('director_ids', [])})
        if filters.get('collection_ids'):
            groups.append({'collection_ids': filters.get('collection_ids', [])})

        results = []
        for g in groups:
            results.extend(self.discover_with_filters(g, page=1, mode='or'))

        results = self._dedupe_movies(results)
        results.sort(key=lambda x: float(x.get('vote_average') or 0.0), reverse=True)
        return results

    def _not_search(self, filters):
        base = []
        for p in range(1, 4):
            base.extend(self.get_popular(page=p))
        base = self._dedupe_movies(base)

        has_filters = any([
            filters.get('genre_ids'),
            filters.get('keyword_ids'),
            filters.get('actor_ids'),
            filters.get('director_ids'),
            filters.get('collection_ids'),
        ])
        if not has_filters:
            return base

        excluded = self._or_search(filters)
        excluded_ids = {int(m.get('id', 0) or 0) for m in excluded if m.get('id')}
        return [m for m in base if int(m.get('id', 0) or 0) not in excluded_ids]

    def hero_search(self, filters, logic_mode='and'):
        """Pipeline principal del buscador avanzado con degradacion progresiva (fallbacks)."""
        filters = filters or {}
        mode = str(logic_mode or 'and').strip().lower()
        if mode not in ('and', 'or', 'not'):
            mode = 'and'

        if mode == 'and':
            strict = self.discover_with_filters(filters, page=1, mode='and')
            strict = self._expand_movie_details(strict[:40], limit=24)
            return {'fallback': False if strict else True, 'results': strict}

        if mode == 'or':
            union = self._or_search(filters)
            union = self._expand_movie_details(union[:40], limit=24)
            return {'fallback': False if union else True, 'results': union}

        if mode == 'not':
            excluded = self._not_search(filters)
            excluded = self._expand_movie_details(excluded[:40], limit=24)
            return {'fallback': False if excluded else True, 'results': excluded}

        strict = self.discover_with_filters(filters, page=1, mode='and')
        if strict:
            strict = self._expand_movie_details(strict[:40], limit=24)
            return {'fallback': False, 'results': strict}

        relaxed = dict(filters)
        relaxed['actor_ids'] = []
        relaxed['director_ids'] = []
        near = self.discover_with_filters(relaxed, page=1, mode='and')
        if near:
            near = self._expand_movie_details(near[:40], limit=24)
            return {'fallback': True, 'results': near}

        relaxed['keyword_ids'] = []
        near2 = self.discover_with_filters(relaxed, page=1, mode='and')
        if near2:
            near2 = self._expand_movie_details(near2[:40], limit=24)
            return {'fallback': True, 'results': near2}

        seed_names = []
        for key in ('genres', 'keywords', 'actors', 'directors', 'collections'):
            for it in filters.get(key, []):
                if isinstance(it, dict) and it.get('name'):
                    name = str(it.get('name'))
                    name = name.replace(' - Colección', '').replace(' - Collection', '').strip()
                    seed_names.append(name)
        if seed_names:
            query = ' '.join(seed_names[:3])
            text_hits = self.search_movies(query, page=1)
            if text_hits:
                text_hits = self._expand_movie_details(text_hits[:40], limit=24)
                return {'fallback': True, 'results': text_hits[:20]}

        return {'fallback': True, 'results': []}

    def recommend_from_history(self, history, limit=10):
        """Genera candidatos desde historial y rankea con mezcla base + BM25."""
        history = [h for h in (history or []) if h.get('id')]
        if not history:
            return []

        recency = [1.0, 0.85, 0.7, 0.55, 0.4]
        reaction_w = {'double_like': 1.25, 'like': 1.0, 'dislike': 0.55}

        candidate_map = {}
        seen_ids = {int(h.get('id')) for h in history if h.get('id')}

        for idx, h in enumerate(history[:5]):
            movie_id = int(h.get('id'))
            details = self.get_movie_details(movie_id, include_related=True)
            source_weight = recency[idx] if idx < len(recency) else 0.3
            rw = reaction_w.get(h.get('reaccion', 'like'), 1.0)
            base_w = source_weight * rw

            for source_mult, group in ((1.0, details.get('recommendations', [])), (0.75, details.get('similar', []))):
                for cand in group:
                    cid = int(cand.get('id') or 0)
                    if not cid or cid in seen_ids:
                        continue
                    if cid not in candidate_map:
                        candidate_map[cid] = {
                            'movie': cand,
                            'base': 0.0,
                        }
                    candidate_map[cid]['base'] += base_w * source_mult

        if not candidate_map:
            return []

        query_terms = self._build_query_terms_from_history(history[:5])
        docs_terms = {cid: self._candidate_terms(v['movie']) for cid, v in candidate_map.items()}
        bm25_raw = self._bm25_scores(query_terms, docs_terms)
        base_raw = {cid: v['base'] for cid, v in candidate_map.items()}

        bm25_n = self._normalize_scores(bm25_raw)
        base_n = self._normalize_scores(base_raw)

        results = []
        for cid, data in candidate_map.items():
            movie = dict(data['movie'])
            score = 0.6 * base_n.get(cid, 0.0) + 0.4 * bm25_n.get(cid, 0.0)
            movie['score_final'] = round(score, 4)
            results.append(movie)

        results.sort(key=lambda x: x.get('score_final', 0), reverse=True)
        return results[:limit]
