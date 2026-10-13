from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Explicacion:
    score_final: float = 0.0

    # Componentes del score (valor ya ponderado)
    expl_cast: float = 0.0
    expl_saga: float = 0.0
    expl_genres: float = 0.0
    expl_dir: float = 0.0
    expl_reaccion: float = 0.0
    expl_tiempo: float = 0.0
    expl_semantic: float = 0.0
    expl_intent: float = 0.0
    expl_quality: float = 0.0

    # Contexto legible
    shared_cast: List[str] = field(default_factory=list)
    shared_genres: List[str] = field(default_factory=list)
    same_director: bool = False
    same_saga: bool = False
    saga_name: str = ''

    # Texto natural (se rellena por motor_explicacion)
    texto_natural: str = ''
    formula_texto: str = ''

    # Trazabilidad IR: tecnica -> contribucion al score (0-1)
    # Claves: 'jaccard', 'jaccard_idf', 'bm25', 'semantica', 'intent'
    ir_tecnicas: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'score_final': round(self.score_final, 4),
            'expl_cast': round(self.expl_cast, 4),
            'expl_saga': round(self.expl_saga, 4),
            'expl_genres': round(self.expl_genres, 4),
            'expl_dir': round(self.expl_dir, 4),
            'expl_reaccion': round(self.expl_reaccion, 4),
            'expl_tiempo': round(self.expl_tiempo, 4),
            'expl_semantic': round(self.expl_semantic, 4),
            'expl_intent': round(self.expl_intent, 4),
            'expl_quality': round(self.expl_quality, 4),
            'shared_cast': self.shared_cast,
            'shared_genres': self.shared_genres,
            'same_director': self.same_director,
            'same_saga': self.same_saga,
            'saga_name': self.saga_name,
            'texto_natural': self.texto_natural,
            'formula_texto': self.formula_texto,
            'ir_tecnicas': self.ir_tecnicas,
        }
