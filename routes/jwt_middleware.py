"""
jwt_middleware - Fase 2.

Decorador jwt_required para proteger endpoints /api/* con Bearer token.
Uso:
    from routes.jwt_middleware import jwt_required

    @bp.route('/api/algo')
    @jwt_required
    def mi_endpoint(usuario):
        return jsonify({'user': usuario.username})
"""
from functools import wraps

from flask import jsonify, request, session, g

_auth_service = None


def init_jwt_middleware(auth_service):
    """Inyecta el AuthService que usa el middleware."""
    global _auth_service
    _auth_service = auth_service


def _resolve_usuario():
    """Resuelve el usuario autenticado desde Bearer token o sesión Flask.

    Orden de prioridad:
      1. Bearer token en Authorization header (compatibilidad API externa)
      2. Sesión Flask (cookie HttpOnly del servidor — método principal)
    """
    if _auth_service is None:
        return None
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[len('Bearer '):]
        return _auth_service.verify_token(token)
    # Fallback: sesión Flask (cookie segura)
    return _auth_service.get_usuario_actual(session)


def jwt_required(f):
    """Decorator que exige autenticación via Bearer token O sesión Flask.

    Si el usuario está autenticado, lo pasa como primer argumento a la función.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if _auth_service is None:
            return jsonify({'error': 'Auth no configurado'}), 503

        usuario = _resolve_usuario()
        if usuario is None:
            return jsonify({'error': 'Autenticación requerida'}), 401

        g.usuario = usuario
        return f(usuario, *args, **kwargs)
    return wrapper


def jwt_optional(f):
    """Decorator que intenta autenticar pero no falla si no hay sesión.

    Pasa el Usuario (o None) como primer argumento a la función.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        usuario = _resolve_usuario()
        g.usuario = usuario
        return f(usuario, *args, **kwargs)
    return wrapper
