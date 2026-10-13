from dataclasses import dataclass, field
from typing import List


@dataclass
class Pelicula:
    id: int
    titulo: str
    generos: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    actores: List[str] = field(default_factory=list)
    director: str = ''
    coleccion_id: int = 0
    coleccion_nombre: str = ''
    poster_path: str = ''
    runtime: float = 0.0
    vote_average: float = 0.0
    overview: str = ''
    release_date: str = ''

    @classmethod
    def from_dict(cls, d: dict) -> 'Pelicula':
        """Construye una Pelicula desde el dict interno de la app (compatible con tmdb_service)."""
        return cls(
            id=int(d.get('id', 0) or 0),
            titulo=str(d.get('title', '') or ''),
            generos=list(d.get('genres_list', []) or []),
            keywords=list(d.get('keywords_list', []) or []),
            actores=list(d.get('cast_list', []) or []),
            director=str(d.get('director', '') or ''),
            coleccion_id=int(d.get('collection_id', 0) or 0),
            coleccion_nombre=str(d.get('collection_name', '') or ''),
            poster_path=str(d.get('poster_path', '') or ''),
            runtime=float(d.get('runtime', 0) or 0),
            vote_average=float(d.get('vote_average', 0) or 0),
            overview=str(d.get('overview', '') or ''),
            release_date=str(d.get('release_date', '') or ''),
        )

    def to_dict(self) -> dict:
        """Convierte a dict interno compatible con el resto de la app."""
        return {
            'id': self.id,
            'title': self.titulo,
            'genres_list': self.generos,
            'keywords_list': self.keywords,
            'cast_list': self.actores,
            'director': self.director,
            'collection_id': self.coleccion_id,
            'collection_name': self.coleccion_nombre,
            'poster_path': self.poster_path,
            'runtime': self.runtime,
            'vote_average': self.vote_average,
            'overview': self.overview,
            'release_date': self.release_date,
        }
