from dataclasses import dataclass, field
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from models.explicacion import Explicacion


@dataclass
class NodoRecomendacion:
    """Nodo del arbol binario de recomendacion.

    Rama izquierda: profundidad (mismo genero).
    Rama derecha: exploracion (genero relacionado).
    """
    pelicula_id: int
    titulo: str
    score: float = 0.0
    tipo: str = 'depth'          # 'depth' | 'exploration'
    profundidad: int = 0
    explicacion: Optional['Explicacion'] = None

    izquierda: Optional['NodoRecomendacion'] = field(default=None, repr=False)
    derecha: Optional['NodoRecomendacion'] = field(default=None, repr=False)

    def es_hoja(self) -> bool:
        return self.izquierda is None and self.derecha is None

    def camino(self) -> List[str]:
        """Retorna el camino desde este nodo hasta sus hojas (para explicabilidad)."""
        if self.es_hoja():
            return [self.titulo]
        path = [self.titulo]
        if self.izquierda:
            path.extend(self.izquierda.camino())
        if self.derecha:
            path.extend(self.derecha.camino())
        return path
