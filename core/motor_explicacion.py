"""
MotorExplicacion - Genera explicaciones legibles para cada recomendacion.

Para cada pelicula recomendada produce:
  - formula_texto: la formula con valores reales (tecnico)
  - texto_natural: frase en lenguaje natural (usuario final)
  - breakdown:     desglose de componentes (para UI)
"""
from models.explicacion import Explicacion


class MotorExplicacion:
    """Convierte un dict de scores en una Explicacion con texto natural y formula."""

    def generar(
        self,
        scores: dict,
        pelicula_candidata: dict,
        pelicula_semilla: dict,
    ) -> Explicacion:
        """Genera una Explicacion completa a partir del dict de scores.

        Args:
            scores:             Resultado de evaluar_matriz_recomendacion().
            pelicula_candidata: Dict interno de la pelicula recomendada.
            pelicula_semilla:   Dict interno de la pelicula que origino la recomendacion.
        """
        exp = Explicacion(
            score_final   = scores.get('score_final',   0.0),
            expl_cast     = scores.get('expl_cast',     0.0),
            expl_saga     = scores.get('expl_saga',     0.0),
            expl_genres   = scores.get('expl_genres',   0.0),
            expl_dir      = scores.get('expl_dir',      0.0),
            expl_reaccion = scores.get('expl_reaccion', 0.0),
            expl_tiempo   = scores.get('expl_tiempo',   0.0),
            expl_semantic = scores.get('expl_semantic', 0.0),
            expl_intent   = scores.get('expl_intent',   0.0),
            expl_quality  = scores.get('expl_quality',  0.0),
            shared_cast   = scores.get('shared_cast',   []),
            shared_genres = scores.get('shared_genres', []),
            same_director = scores.get('same_director', False),
            same_saga     = scores.get('same_saga',     False),
            saga_name     = scores.get('saga_name',     ''),
        )

        exp.formula_texto  = self._formula(exp)
        exp.texto_natural  = self._texto_natural(exp, pelicula_candidata, pelicula_semilla)
        exp.ir_tecnicas    = self._ir_tecnicas(exp)
        return exp

    # ------------------------------------------------------------------
    # Formula tecnica
    # ------------------------------------------------------------------

    @staticmethod
    def _formula(exp: Explicacion) -> str:
        """Genera la formula con valores reales, p.ej.:
        Score = (0.15×cast) + (0.10×saga) + ... = 0.72
        """
        componentes = [
            f"(cast:{exp.expl_cast:.3f})",
            f"(saga:{exp.expl_saga:.3f})",
            f"(gen:{exp.expl_genres:.3f})",
            f"(dir:{exp.expl_dir:.3f})",
            f"(reacc:{exp.expl_reaccion:.3f})",
            f"(tpo:{exp.expl_tiempo:.3f})",
            f"(sem:{exp.expl_semantic:.3f})",
            f"(int:{exp.expl_intent:.3f})",
        ]
        suma = " + ".join(componentes)
        return f"Score = {suma} = {exp.score_final:.4f}"

    # ------------------------------------------------------------------
    # Texto natural
    # ------------------------------------------------------------------

    @staticmethod
    def _texto_natural(
        exp: Explicacion,
        candidata: dict,
        semilla: dict,
    ) -> str:
        """Genera una frase legible explicando por que se recomienda la pelicula."""
        titulo_cand   = str(candidata.get('title', '') or '')
        titulo_semilla = str(semilla.get('title', '') or '')
        razones = []

        if exp.same_saga and exp.saga_name:
            razones.append(f"pertenece a la saga «{exp.saga_name}»")

        if exp.same_director:
            director = str(candidata.get('director', '') or '')
            if director:
                razones.append(f"es del mismo director ({director})")
            else:
                razones.append("es del mismo director")

        if exp.shared_cast:
            actores = ', '.join(exp.shared_cast[:2])
            razones.append(f"comparte actores con «{titulo_semilla}» ({actores})")

        if exp.shared_genres:
            generos = ', '.join(exp.shared_genres[:2])
            razones.append(f"es del mismo genero ({generos})")
        elif exp.expl_genres > 0.05:
            generos_cand = candidata.get('genres_list') or []
            if generos_cand:
                razones.append(f"es una pelicula de {generos_cand[0]}")

        if exp.expl_semantic > 0.08 and not razones:
            razones.append(f"tiene tematica similar a «{titulo_semilla}»")

        if not razones:
            razones.append(f"podria interesarte si disfrutaste «{titulo_semilla}»")

        base = f"Se recomienda «{titulo_cand}» porque " if titulo_cand else "Se recomienda porque "
        return base + " y ".join(razones) + "."

    # ------------------------------------------------------------------
    # Trazabilidad IR
    # ------------------------------------------------------------------

    @staticmethod
    def _ir_tecnicas(exp: Explicacion) -> dict:
        """Mapea cada tecnica IR a su contribucion acumulada en el score final.

        Tecnicas:
          jaccard     — Jaccard simple (overviews y titulos, dentro de sim_semantica)
          jaccard_idf — Jaccard ponderado con IDF (cast y generos)
          bm25        — BM25 (precalculado en tmdb_service; no llega al score directamente,
                        se aproxima por expl_intent que usa similitud tematica token-based)
          semantica   — Similitud semantica combinada (keywords+overview+title)
          intent      — Similitud de intencion tematica (coleccion+keywords+titulo)
        """
        return {
            'jaccard':     round(exp.expl_semantic * 0.35, 4),  # fraccion overview-jaccard dentro de semantica
            'jaccard_idf': round(exp.expl_cast + exp.expl_genres, 4),
            'bm25':        round(exp.expl_intent, 4),           # intent usa terminos BM25-style
            'semantica':   round(exp.expl_semantic, 4),
            'intent':      round(exp.expl_intent, 4),
        }
