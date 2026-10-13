from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class EntradaHistorial:
    pelicula_id: int
    titulo: str
    reaccion: str = 'like'       # 'like' | 'double_like' | 'dislike'
    minutos_vistos: float = 0.0
    progreso: float = 0.0        # 0-100


@dataclass
class Usuario:
    id: int
    username: str
    email: Optional[str] = None
    edad: Optional[int] = None
    rol: str = 'user'            # 'user' | 'admin'
    historial: List[EntradaHistorial] = field(default_factory=list)
