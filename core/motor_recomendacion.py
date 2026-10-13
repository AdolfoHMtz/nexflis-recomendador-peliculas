"""
MotorRecomendacion - Logica central de recomendacion con arbol binario.

Implementa:
  - evaluar_matriz_recomendacion  (extraido de app.py, misma logica)
  - evaluar_matriz_descubrimiento (extraido de app.py, misma logica)
  - ArbolRecomendacion            (nuevo: separa rama depth vs exploration)

El arbol se regenera en cada llamada (no es persistente).
  Rama izquierda: depth      — mismo genero primario, 10 peliculas
  Rama derecha:   exploration — genero relacionado,   10 peliculas
"""
from typing import Dict, List, Optional, Tuple

from core.gestor_dimensiones import GestorDimensiones
from models.nodo_recomendacion import NodoRecomendacion
from models.explicacion import Explicacion


# Pesos del score principal (deben sumar 1.0)
_PESOS = {
    'cast':     0.15,
    'saga':     0.10,
    'generos':  0.15,
    'director': 0.05,
    'reaccion': 0.15,
    'tiempo':   0.10,
    'semantic': 0.20,
    'intent':   0.10,
}

# Pesos del score de exploracion
_PESOS_EXPLORACION = {
    'depth_base':   0.50,
    'transicion':   0.30,
    'novedad':      0.20,
}

_ESCALA_REACCION = {'double_like': 1.0, 'like': 8.0 / 15.0, 'dislike': 0.0}


class MotorRecomendacion:
    """Motor de recomendacion: calcula scores y construye el arbol binario."""

    def __init__(self):
        self._dim = GestorDimensiones()

    # ------------------------------------------------------------------
    # Scoring principal (logica extraida de app.py sin cambios)
    # ------------------------------------------------------------------

    def evaluar_matriz_recomendacion(
        self,
        candidata: dict,
        historial_ref: list,
        reaccion: str = 'like',
        val_tiempo: float = 0.0,
    ) -> dict:
        """Puntua una pelicula candidata contra el historial del usuario.

        Replica exactamente evaluar_matriz_recomendacion() de app.py.
        """
        historial_ref = historial_ref or []
        dim = self._dim

        idf_generos  = dim.idf_from_history(historial_ref, 'genres_list')
        idf_keywords = dim.idf_from_history(historial_ref, 'keywords_list')
        idf_cast     = dim.idf_from_history(historial_ref, 'cast_list')

        cast_cand     = set((candidata.get('cast_list') or [])[:8])
        generos_cand  = set(candidata.get('genres_list') or [])
        director_cand = str(candidata.get('director') or '').strip().lower()
        coleccion_cand = int(candidata.get('collection_id') or 0)

        scores_cast      = []
        scores_generos   = []
        scores_semantica = []
        scores_afinidad  = []

        best_ratio_cast   = 0.0
        best_ratio_generos = 0.0
        cast_compartido_best    = []
        generos_compartidos_best = []
        mismo_director = False
        misma_saga     = False
        nombre_saga    = str(candidata.get('collection_name') or '')

        for peli_base in historial_ref:
            cast_base     = set((peli_base.get('cast_list') or [])[:8])
            generos_base  = set(peli_base.get('genres_list') or [])
            director_base = str(peli_base.get('director') or '').strip().lower()
            coleccion_base = int(peli_base.get('collection_id') or 0)

            cast_inter    = list(cast_cand & cast_base)
            generos_inter = list(generos_cand & generos_base)  # nombres originales para mostrar

            keywords_cand = candidata.get('keywords_list', []) or []
            keywords_base = peli_base.get('keywords_list', []) or []
            ratio_keywords = dim.weighted_jaccard(keywords_cand, keywords_base, idf=idf_keywords)

            ov_tok_cand = dim.tokenize(candidata.get('overview', ''))
            ov_tok_base = dim.tokenize(peli_base.get('overview', ''))
            ratio_overview = dim.jaccard(ov_tok_cand, ov_tok_base)

            ttl_tok_cand = dim.tokenize(candidata.get('title', ''))
            ttl_tok_base = dim.tokenize(peli_base.get('title', ''))
            ratio_title = dim.jaccard(ttl_tok_cand, ttl_tok_base)

            ratio_cast    = dim.weighted_jaccard(cast_cand, cast_base, idf=idf_cast)
            # Géneros: intersección / |géneros_base| (no Jaccard unión)
            # Si base tiene 3 géneros y candidata comparte 2 → 2/3 = 66.6%
            gen_cand_norm = set(str(g).lower().strip() for g in generos_cand)
            gen_base_norm = set(str(g).lower().strip() for g in generos_base)
            inter_gen_count = len(gen_cand_norm & gen_base_norm)
            ratio_generos = inter_gen_count / max(1, len(gen_base_norm))

            ratio_semantica = min(1.0, 0.45 * ratio_keywords + 0.35 * ratio_overview + 0.20 * ratio_title)

            if ratio_cast > best_ratio_cast:
                best_ratio_cast = ratio_cast
                cast_compartido_best = cast_inter[:4]

            if ratio_generos > best_ratio_generos:
                best_ratio_generos = ratio_generos
                generos_compartidos_best = generos_inter[:4]

            scores_cast.append(ratio_cast)
            scores_generos.append(ratio_generos)
            scores_semantica.append(ratio_semantica)
            scores_afinidad.append(dim.intent_similarity(candidata, peli_base))

            if director_cand and director_base and director_cand == director_base:
                mismo_director = True

            if coleccion_cand and coleccion_base and coleccion_cand == coleccion_base:
                misma_saga = True
                if not nombre_saga:
                    nombre_saga = str(peli_base.get('collection_name') or '')

        sim_cast     = dim.robust_aggregate(scores_cast) if scores_cast else min(1.0, best_ratio_cast)
        sim_saga     = 1.0 if misma_saga else 0.0
        sim_generos  = dim.robust_aggregate(scores_generos) if scores_generos else min(1.0, best_ratio_generos)
        sim_director = 1.0 if mismo_director else 0.0
        sim_reaccion = _ESCALA_REACCION.get(reaccion, 8.0 / 15.0)
        sim_tiempo   = max(0.0, min(1.0, float(val_tiempo or 0.0)))
        sim_semantica        = dim.robust_aggregate(scores_semantica)
        sim_afinidad_tematica = dim.robust_aggregate(scores_afinidad)

        expl_cast     = _PESOS['cast']     * sim_cast
        expl_saga     = _PESOS['saga']     * sim_saga
        expl_genres   = _PESOS['generos']  * sim_generos
        expl_dir      = _PESOS['director'] * sim_director
        expl_reaccion = _PESOS['reaccion'] * sim_reaccion
        expl_tiempo   = _PESOS['tiempo']   * sim_tiempo
        expl_semantic = _PESOS['semantic'] * sim_semantica
        expl_intent   = _PESOS['intent']   * sim_afinidad_tematica

        score_final = (expl_cast + expl_saga + expl_genres + expl_dir
                       + expl_reaccion + expl_tiempo + expl_semantic + expl_intent)

        return {
            'expl_cast':     round(expl_cast, 4),
            'expl_saga':     round(expl_saga, 4),
            'expl_genres':   round(expl_genres, 4),
            'expl_dir':      round(expl_dir, 4),
            'expl_reaccion': round(expl_reaccion, 4),
            'expl_tiempo':   round(expl_tiempo, 4),
            'expl_semantic': round(expl_semantic, 4),
            'expl_intent':   round(expl_intent, 4),
            'score_final':   round(score_final, 4),
            'shared_cast':   cast_compartido_best,
            'shared_genres': generos_compartidos_best,
            'same_director': mismo_director,
            'same_saga':     misma_saga,
            'saga_name':     nombre_saga,
            'ir_tecnicas': {
                'jaccard':     round(expl_semantic * 0.35, 4),
                'jaccard_idf': round(expl_cast + expl_genres, 4),
                'bm25':        round(expl_intent, 4),
                'semantica':   round(expl_semantic, 4),
                'intent':      round(expl_intent, 4),
            },
        }

    def evaluar_matriz_descubrimiento(
        self,
        candidata: dict,
        historial_ref: list,
        val_tiempo: float = 0.0,
        diff_opts: Optional[Dict[str, bool]] = None,
    ) -> dict:
        """Puntua una candidata para el modo 'Algo diferente' (dislike).

        Matriz de 6 campos:
          Diff Géneros    20%
          Diff Reparto    20%
          Diff Director   20%
          Diff Temática   20%
          Diff Año        10%
          Calificación    10%

        Si el usuario seleccionó dimensiones en DiffModal (diff_opts), esos campos
        reciben el doble de peso (el score puede superar 100% — es intencional).
        """
        historial_ref = historial_ref or []
        diff_opts = diff_opts or {}
        dim = self._dim

        cast_cand     = set((candidata.get('cast_list') or [])[:8])
        generos_cand  = set(str(g).lower().strip() for g in (candidata.get('genres_list') or []))
        director_cand = str(candidata.get('director') or '').strip().lower()
        year_cand     = int(str(candidata.get('release_date') or '0')[:4] or 0)

        max_sim_cast   = 0.0
        max_sim_generos = 0.0
        max_sim_semantica = 0.0
        cast_compartido_best     = []
        generos_compartidos_best = []
        mismo_director = False
        anno_base_best = 0

        idf_keywords = dim.idf_from_history(historial_ref, 'keywords_list')

        for peli_base in historial_ref:
            cast_base     = set((peli_base.get('cast_list') or [])[:8])
            generos_base  = set(str(g).lower().strip() for g in (peli_base.get('genres_list') or []))
            director_base = str(peli_base.get('director') or '').strip().lower()
            year_base     = int(str(peli_base.get('release_date') or '0')[:4] or 0)

            inter_cast    = list(cast_cand & cast_base)
            inter_generos = list(generos_cand & generos_base)

            sim_gen  = dim.jaccard(list(generos_cand), list(generos_base))
            sim_cast = dim.weighted_jaccard(cast_cand, cast_base)

            kw_sim = dim.weighted_jaccard(
                candidata.get('keywords_list', []) or [],
                peli_base.get('keywords_list', []) or [],
                idf=idf_keywords,
            )
            ov_sim = dim.jaccard(
                dim.tokenize(candidata.get('overview', '')),
                dim.tokenize(peli_base.get('overview', '')),
            )
            sim_semantica = min(1.0, 0.6 * kw_sim + 0.4 * ov_sim)

            if sim_cast > max_sim_cast:
                max_sim_cast = sim_cast
                cast_compartido_best = inter_cast[:4]
            if sim_gen > max_sim_generos:
                max_sim_generos = sim_gen
                generos_compartidos_best = inter_generos[:4]
            if sim_semantica > max_sim_semantica:
                max_sim_semantica = sim_semantica

            if director_cand and director_base and director_cand == director_base:
                mismo_director = True
            if year_base:
                anno_base_best = year_base

        diff_generos   = 1.0 - min(1.0, max_sim_generos)
        diff_cast      = 1.0 - min(1.0, max_sim_cast)
        diff_director  = 0.0 if mismo_director else 1.0
        diff_semantica = 1.0 - min(1.0, max_sim_semantica)

        # Diff año: binario — mismo año → 0 (nada diferente), distinto → 1 (completamente diferente)
        if year_cand and anno_base_best:
            diff_anno = 0.0 if year_cand == anno_base_best else 1.0
        else:
            diff_anno = 0.5  # desconocido → neutral

        quality_norm = max(0.0, min(1.0, float(candidata.get('vote_average', 0) or 0) / 10.0))

        # Pesos base
        w_generos   = 0.20
        w_cast      = 0.20
        w_director  = 0.20
        w_semantica = 0.20
        w_anno      = 0.10
        w_quality   = 0.10

        # Boost x2 para dimensiones que el usuario eligió en DiffModal
        if diff_opts.get('diff_genero'):    w_generos   *= 2
        if diff_opts.get('diff_cast'):      w_cast      *= 2
        if diff_opts.get('diff_director'):  w_director  *= 2
        if diff_opts.get('diff_semantica'): w_semantica *= 2
        if diff_opts.get('diff_epoca'):     w_anno      *= 2

        expl_genres    = w_generos   * diff_generos
        expl_cast      = w_cast      * diff_cast
        expl_dir       = w_director  * diff_director
        expl_semantic  = w_semantica * diff_semantica
        expl_anno      = w_anno      * diff_anno
        expl_quality   = w_quality   * quality_norm
        score_final    = expl_genres + expl_cast + expl_dir + expl_semantic + expl_anno + expl_quality

        return {
            'expl_cast':       round(expl_cast, 4),
            'expl_saga':       round(expl_anno, 4),      # reutilizamos expl_saga para diff año
            'expl_quality':    round(expl_quality, 4),
            'expl_genres':     round(expl_genres, 4),
            'expl_dir':        round(expl_dir, 4),
            'expl_reaccion':   0.0,
            'expl_semantic':   round(expl_semantic, 4),
            'expl_intent':     round(expl_anno, 4),      # reutilizamos expl_intent para diff año en UI
            'expl_tiempo':     round(expl_quality, 4),   # reutilizamos expl_tiempo para calidad en UI
            'score_final':     round(score_final, 4),
            'shared_cast':     cast_compartido_best,
            'shared_genres':   generos_compartidos_best,
            'same_director':   mismo_director,
            'same_saga':       False,
            'saga_name':       '',
            'reaccion_label':  'No me gustó',
            'val_reaccion':    0.0,
            'val_tiempo':      round(quality_norm, 3),
            'diff_generos':    round(diff_generos, 4),
            'diff_cast':       round(diff_cast, 4),
            'diff_director':   round(diff_director, 4),
            'diff_semantica':  round(diff_semantica, 4),
            'diff_anno':       round(diff_anno, 4),
            'ir_tecnicas': {
                'jaccard':     round(expl_cast + expl_genres, 4),
                'jaccard_idf': round(expl_cast, 4),
                'bm25':        0.0,
                'semantica':   round(expl_semantic, 4),
                'intent':      0.0,
            },
        }

    # ------------------------------------------------------------------
    # Score de exploracion (nuevo — rama derecha del arbol)
    # ------------------------------------------------------------------

    def score_exploracion(
        self,
        score_depth: float,
        genero_origen: str,
        genero_destino: str,
        novedad: float = 0.5,
    ) -> float:
        """Calcula el score para la rama de exploracion del arbol.

        SCORE_EXPLORATION = (score_depth × 0.5) + (peso_transicion × 0.3) + (novedad × 0.2)
        """
        peso_trans = GestorDimensiones.peso_transicion(genero_origen, genero_destino)
        return (
            _PESOS_EXPLORACION['depth_base'] * score_depth
            + _PESOS_EXPLORACION['transicion'] * peso_trans
            + _PESOS_EXPLORACION['novedad']    * novedad
        )

    # ------------------------------------------------------------------
    # Arbol binario de recomendacion
    # ------------------------------------------------------------------

    def construir_arbol(
        self,
        peli_semilla: dict,
        candidatas_depth: List[dict],
        candidatas_exploracion: List[dict],
        historial: list,
        reaccion: str = 'like',
        val_tiempo: float = 0.0,
        max_depth: int = 4,
    ) -> Optional[NodoRecomendacion]:
        """Construye el arbol binario de recomendacion.

        Rama izquierda (depth):      candidatas del mismo genero.
        Rama derecha  (exploration): candidatas de genero relacionado.
        Profundidad maxima: max_depth niveles.

        Retorna la raiz del arbol.
        """
        genero_semilla = (peli_semilla.get('genres_list') or [''])[0]

        raiz = NodoRecomendacion(
            pelicula_id=int(peli_semilla.get('id', 0)),
            titulo=str(peli_semilla.get('title', '')),
            score=1.0,
            tipo='seed',
            profundidad=0,
        )

        raiz.izquierda = self._construir_rama_depth(
            candidatas_depth, historial, reaccion, val_tiempo,
            profundidad=1, max_depth=max_depth,
        )

        raiz.derecha = self._construir_rama_exploracion(
            candidatas_exploracion, historial, genero_semilla,
            reaccion, val_tiempo, profundidad=1, max_depth=max_depth,
        )

        return raiz

    def _construir_rama_depth(
        self,
        candidatas: List[dict],
        historial: list,
        reaccion: str,
        val_tiempo: float,
        profundidad: int,
        max_depth: int,
    ) -> Optional[NodoRecomendacion]:
        if profundidad > max_depth or not candidatas:
            return None

        scored = []
        for c in candidatas:
            exp = self.evaluar_matriz_recomendacion(c, historial, reaccion, val_tiempo)
            scored.append((c, exp))
        scored.sort(key=lambda x: x[1]['score_final'], reverse=True)

        mejor_cand, mejor_exp = scored[0]
        nodo = NodoRecomendacion(
            pelicula_id=int(mejor_cand.get('id', 0)),
            titulo=str(mejor_cand.get('title', '')),
            score=mejor_exp['score_final'],
            tipo='depth',
            profundidad=profundidad,
        )

        resto = [c for c, _ in scored[1:]]
        nodo.izquierda = self._construir_rama_depth(
            resto, historial, reaccion, val_tiempo,
            profundidad + 1, max_depth,
        )
        return nodo

    def _construir_rama_exploracion(
        self,
        candidatas: List[dict],
        historial: list,
        genero_origen: str,
        reaccion: str,
        val_tiempo: float,
        profundidad: int,
        max_depth: int,
    ) -> Optional[NodoRecomendacion]:
        if profundidad > max_depth or not candidatas:
            return None

        scored = []
        for c in candidatas:
            exp     = self.evaluar_matriz_recomendacion(c, historial, reaccion, val_tiempo)
            generos = c.get('genres_list') or []
            genero_dest = generos[0] if generos else ''
            score_exp = self.score_exploracion(
                exp['score_final'], genero_origen, genero_dest
            )
            scored.append((c, exp, score_exp))
        scored.sort(key=lambda x: x[2], reverse=True)

        mejor_cand, mejor_exp, mejor_score = scored[0]
        nodo = NodoRecomendacion(
            pelicula_id=int(mejor_cand.get('id', 0)),
            titulo=str(mejor_cand.get('title', '')),
            score=mejor_score,
            tipo='exploration',
            profundidad=profundidad,
        )

        resto = [c for c, _, _ in scored[1:]]
        nodo.derecha = self._construir_rama_exploracion(
            resto, historial, genero_origen, reaccion, val_tiempo,
            profundidad + 1, max_depth,
        )
        return nodo

    # ------------------------------------------------------------------
    # Extraccion de listas desde el arbol
    # ------------------------------------------------------------------

    def extraer_depth(self, raiz: Optional[NodoRecomendacion], n: int = 10) -> List[NodoRecomendacion]:
        """Recorre la rama izquierda y retorna hasta n nodos depth."""
        nodos = []
        self._recorrer_izquierda(raiz.izquierda if raiz else None, nodos, n)
        return nodos

    def extraer_exploracion(self, raiz: Optional[NodoRecomendacion], n: int = 10) -> List[NodoRecomendacion]:
        """Recorre la rama derecha y retorna hasta n nodos exploration."""
        nodos = []
        self._recorrer_derecha(raiz.derecha if raiz else None, nodos, n)
        return nodos

    def _recorrer_izquierda(self, nodo, acum, limite):
        if nodo is None or len(acum) >= limite:
            return
        acum.append(nodo)
        self._recorrer_izquierda(nodo.izquierda, acum, limite)

    def _recorrer_derecha(self, nodo, acum, limite):
        if nodo is None or len(acum) >= limite:
            return
        acum.append(nodo)
        self._recorrer_derecha(nodo.derecha, acum, limite)
