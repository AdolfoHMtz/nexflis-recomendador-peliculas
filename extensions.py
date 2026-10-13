"""
Extensiones Flask compartidas entre app.py y los módulos de rutas.
Se inicializan aquí sin app para evitar importaciones circulares.
Flask-Limiter 4.x requiere que el decorador @limiter.limit se aplique
en tiempo de definición de la función — por eso el objeto debe existir
antes de que los módulos de rutas sean importados.
"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri='memory://',
)
