"""
Logging centralizado para NEXFLIS.

Uso en cualquier módulo:
    from core.logger import get_logger
    logger = get_logger(__name__)
    logger.error("Falló X", exc_info=True)

Niveles:
  - DEBUG   : detalles internos (loops, conversiones menores)
  - INFO    : operaciones normales relevantes (startup, login, visionado guardado)
  - WARNING : situaciones inesperadas pero recuperables (cache miss, fallback activado)
  - ERROR   : fallos que impiden completar una operación (DB error, TMDB error)
  - CRITICAL: fallos que comprometen el servicio completo (no se usan actualmente)

Destinos:
  - Consola (StreamHandler): nivel INFO y superior
  - Archivo logs/nexflis.log (RotatingFileHandler): nivel DEBUG y superior,
    rotación a 5 MB, máximo 3 archivos históricos
"""
import logging
import logging.handlers
import os
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parent.parent / 'logs'
_LOG_FILE = _LOG_DIR / 'nexflis.log'
_LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

_configured = False


def _setup():
    global _configured
    if _configured:
        return

    _LOG_DIR.mkdir(exist_ok=True)

    root = logging.getLogger('nexflis')
    root.setLevel(logging.DEBUG)

    # Consola: INFO+
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    root.addHandler(console)

    # Archivo rotativo: DEBUG+
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            _LOG_FILE,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding='utf-8',
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
        root.addHandler(file_handler)
    except OSError:
        # Si no se puede escribir el archivo (permisos, etc.), solo usamos consola
        root.warning('No se pudo crear el archivo de log en %s — usando solo consola', _LOG_FILE)

    # Silenciar loggers externos ruidosos
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Retorna un logger bajo el namespace 'nexflis.<name>'."""
    _setup()
    # Normalizar: 'services.db_service' -> 'nexflis.services.db_service'
    if not name.startswith('nexflis'):
        name = f'nexflis.{name}'
    return logging.getLogger(name)
