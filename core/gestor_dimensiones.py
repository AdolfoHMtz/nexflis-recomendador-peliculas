"""
GestorDimensiones - Logica de similitud y transiciones entre generos.

Contiene las funciones de IR extraidas de app.py:
  - Jaccard simple y ponderado (con IDF)
  - IDF calculado desde historial
  - Similitud de intencion tematica
  - Transiciones entre generos (grafo direccional)
  - Calculo de distancia entre dimensiones (0-1)
"""
import math
import re
from collections import Counter
from typing import Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Stopwords compartidas (mismas que app.py)
# ---------------------------------------------------------------------------

_STOPWORDS: Set[str] = {
    'de', 'la', 'el', 'los', 'las', 'del', 'y', 'a', 'en', 'un', 'una', 'the', 'of',
    'and', 'to', 'for', 'con', 'por', 'para', 'es', 'is', 'movie', 'pelicula', 'film',
    'with', 'como', 'sobre', 'una', 'un',
}

_GENERIC_TITLE_TERMS: Set[str] = {
    'living', 'story', 'stories', 'chronicles', 'documentary', 'part', 'chapter',
    'life', 'lives', 'unknown', 'new', 'old', 'final', 'rise', 'fall',
}

# ---------------------------------------------------------------------------
# Grafo de transiciones entre generos (direccional)
# Cada genero apunta a los generos "relacionados" para la rama de exploracion.
# ---------------------------------------------------------------------------

TRANSICIONES_GENEROS: Dict[str, List[str]] = {
    'Terror':       ['Suspenso', 'Thriller', 'Misterio', 'Ciencia ficción'],
    'Horror':       ['Thriller', 'Mystery', 'Science Fiction', 'Drama'],
    'Acción':       ['Aventura', 'Thriller', 'Ciencia ficción', 'Crimen'],
    'Action':       ['Adventure', 'Thriller', 'Science Fiction', 'Crime'],
    'Comedia':      ['Romance', 'Familia', 'Animación', 'Drama'],
    'Comedy':       ['Romance', 'Family', 'Animation', 'Drama'],
    'Drama':        ['Romance', 'Thriller', 'Crimen', 'Historia'],
    'Romance':      ['Drama', 'Comedia', 'Familia'],
    'Thriller':     ['Misterio', 'Crimen', 'Acción', 'Terror'],
    'Mystery':      ['Thriller', 'Crime', 'Drama', 'Horror'],
    'Ciencia ficción': ['Acción', 'Aventura', 'Thriller', 'Fantasía'],
    'Science Fiction': ['Action', 'Adventure', 'Thriller', 'Fantasy'],
    'Fantasía':     ['Aventura', 'Acción', 'Animación', 'Familia'],
    'Fantasy':      ['Adventure', 'Action', 'Animation', 'Family'],
    'Aventura':     ['Acción', 'Fantasía', 'Familia', 'Ciencia ficción'],
    'Adventure':    ['Action', 'Fantasy', 'Family', 'Science Fiction'],
    'Animación':    ['Familia', 'Comedia', 'Fantasía', 'Aventura'],
    'Animation':    ['Family', 'Comedy', 'Fantasy', 'Adventure'],
    'Familia':      ['Animación', 'Comedia', 'Aventura', 'Fantasía'],
    'Family':       ['Animation', 'Comedy', 'Adventure', 'Fantasy'],
    'Crimen':       ['Thriller', 'Drama', 'Misterio', 'Acción'],
    'Crime':        ['Thriller', 'Drama', 'Mystery', 'Action'],
    'Historia':     ['Drama', 'Guerra', 'Documental'],
    'History':      ['Drama', 'War', 'Documentary'],
    'Guerra':       ['Drama', 'Historia', 'Acción'],
    'War':          ['Drama', 'History', 'Action'],
    'Documental':   ['Historia', 'Drama'],
    'Documentary':  ['History', 'Drama'],
    'Música':       ['Drama', 'Documental', 'Comedia'],
    'Music':        ['Drama', 'Documentary', 'Comedy'],
    'Western':      ['Acción', 'Aventura', 'Drama'],
}


class GestorDimensiones:
    """Calcula similitudes entre peliculas y gestiona transiciones entre generos."""

    # ------------------------------------------------------------------
    # Utilidades de texto
    # ------------------------------------------------------------------

    @staticmethod
    def tokenize(text: str) -> List[str]:
        raw = str(text or '').lower()
        return [t for t in re.findall(r"[a-z0-9áéíóúñ]+", raw) if len(t) >= 2]

    @staticmethod
    def normalize_terms(values) -> List[str]:
        return [str(v).strip().lower() for v in (values or []) if str(v).strip()]

    # ------------------------------------------------------------------
    # Jaccard
    # ------------------------------------------------------------------

    @staticmethod
    def jaccard(a, b) -> float:
        sa = set(a or [])
        sb = set(b or [])
        if not sa or not sb:
            return 0.0
        return len(sa & sb) / max(1, len(sa | sb))

    @staticmethod
    def weighted_jaccard(a, b, idf: Optional[Dict[str, float]] = None) -> float:
        """Jaccard ponderado por IDF: terminos raros aportan mas que terminos comunes."""
        sa = set(GestorDimensiones.normalize_terms(a))
        sb = set(GestorDimensiones.normalize_terms(b))
        if not sa or not sb:
            return 0.0

        inter = sa & sb
        union = sa | sb
        idf = idf or {}

        num = sum(float(idf.get(t, 1.0)) for t in inter)
        den = sum(float(idf.get(t, 1.0)) for t in union)
        return num / den if den > 1e-9 else 0.0

    # ------------------------------------------------------------------
    # IDF desde historial
    # ------------------------------------------------------------------

    @staticmethod
    def idf_from_history(historial: list, campo: str) -> Dict[str, float]:
        """Calcula IDF de un campo (generos, keywords, cast) desde el historial."""
        docs = []
        for h in (historial or []):
            terms = set(GestorDimensiones.normalize_terms(h.get(campo, []) or []))
            if terms:
                docs.append(terms)

        n_docs = len(docs)
        if n_docs <= 0:
            return {}

        df = Counter()
        for terms in docs:
            for term in terms:
                df[term] += 1

        return {
            term: math.log(1.0 + ((n_docs + 1.0) / (dfi + 1.0)))
            for term, dfi in df.items()
        }

    # ------------------------------------------------------------------
    # Similitud de intencion tematica
    # ------------------------------------------------------------------

    @staticmethod
    def _intent_terms(movie: dict) -> dict:
        tok = GestorDimensiones.tokenize
        sw = _STOPWORDS
        return {
            'title':       [t for t in tok(movie.get('title', '')) if t not in sw],
            'keywords':    [t for kw in (movie.get('keywords_list') or [])
                            for t in tok(kw) if t not in sw],
            'overview':    [t for t in tok(movie.get('overview', '')) if t not in sw],
            'collection':  [t for t in tok(movie.get('collection_name', '')) if t not in sw],
            'collection_id': int(movie.get('collection_id') or 0),
        }

    @classmethod
    def intent_similarity(cls, candidata: dict, semilla: dict) -> float:
        """Similitud tematica entre candidata y pelicula semilla (0-1)."""
        c = cls._intent_terms(candidata)
        s = cls._intent_terms(semilla)

        same_coll = 1.0 if (c['collection_id'] and s['collection_id']
                            and c['collection_id'] == s['collection_id']) else 0.0
        kw_sim  = cls.jaccard(c['keywords'],   s['keywords'])
        ttl_sim = cls.jaccard(c['title'],       s['title'])
        col_sim = cls.jaccard(c['collection'],  s['collection'])
        ov_sim  = cls.jaccard(c['overview'],    s['overview'])

        return min(1.0, 0.40 * same_coll + 0.30 * kw_sim
                   + 0.15 * col_sim + 0.10 * ttl_sim + 0.05 * ov_sim)

    # ------------------------------------------------------------------
    # Agregacion robusta top-2
    # ------------------------------------------------------------------

    @staticmethod
    def robust_aggregate(values: list) -> float:
        """Promedio ponderado top-2 para no depender de una sola pelicula del historial."""
        vals = sorted([float(v) for v in (values or []) if v is not None], reverse=True)
        if not vals:
            return 0.0
        if len(vals) == 1:
            return max(0.0, min(1.0, vals[0]))
        return max(0.0, min(1.0, 0.65 * vals[0] + 0.35 * vals[1]))

    # ------------------------------------------------------------------
    # Transiciones entre generos (para rama de exploracion)
    # ------------------------------------------------------------------

    @staticmethod
    def generos_relacionados(genero: str) -> List[str]:
        """Retorna generos de exploracion para un genero dado."""
        return TRANSICIONES_GENEROS.get(genero, [])

    @staticmethod
    def distancia_generos(genero_a: str, genero_b: str) -> float:
        """Distancia entre dos generos (0 = identicos, 1 = sin relacion).

        0.0  — mismo genero
        0.3  — relacion directa en el grafo
        0.6  — relacion indirecta (2 saltos)
        1.0  — sin relacion
        """
        if genero_a == genero_b:
            return 0.0
        vecinos_a = set(TRANSICIONES_GENEROS.get(genero_a, []))
        if genero_b in vecinos_a:
            return 0.3
        # Segundo nivel: vecinos de vecinos
        for vecino in vecinos_a:
            if genero_b in set(TRANSICIONES_GENEROS.get(vecino, [])):
                return 0.6
        return 1.0

    @staticmethod
    def peso_transicion(genero_origen: str, genero_destino: str) -> float:
        """Peso de la transicion para el score de exploracion (0-1, inverso de distancia)."""
        d = GestorDimensiones.distancia_generos(genero_origen, genero_destino)
        return max(0.0, 1.0 - d)
