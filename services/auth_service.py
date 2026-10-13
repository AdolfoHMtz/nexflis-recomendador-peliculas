"""
AuthService - Fase 2.


Responsabilidades:
  - Registro de usuarios con hash bcrypt
  - Login con verificacion de password
  - Lectura del usuario actual desde session de Flask
  - Logout
  - Generacion y verificacion de JWT para uso en /api/*
"""
import os
import datetime
from typing import Optional

from core.logger import get_logger

logger = get_logger(__name__)

try:
    import bcrypt
    _BCRYPT_AVAILABLE = True
except ImportError:
    _BCRYPT_AVAILABLE = False

try:
    import jwt as pyjwt
    _JWT_AVAILABLE = True
except ImportError:
    _JWT_AVAILABLE = False

from models.usuario import Usuario

_JWT_SECRET_DEFAULT = "nexflis_jwt_secret_changeme"
_JWT_ALGORITHM = "HS256"
_JWT_EXPIRY_HOURS = 24


class AuthService:
    """Servicio de autenticacion basado en session de Flask + bcrypt + JWT."""

    def __init__(self, db_service=None, jwt_secret: str = None):
        self._db = db_service
        self._jwt_secret = jwt_secret or os.getenv('JWT_SECRET', _JWT_SECRET_DEFAULT)

    # ------------------------------------------------------------------
    # Session
    # ------------------------------------------------------------------

    def get_usuario_actual(self, session: dict) -> Optional[Usuario]:
        """Retorna el Usuario de la sesion, o None si no esta autenticado."""
        user_id = session.get('user_id')
        if not user_id or not self._db:
            return None
        row = self._db.get_user_by_id(int(user_id))
        if not row:
            return None
        return Usuario(
            id=row['id'],
            username=row['username'],
            email=row.get('email'),
            edad=row.get('edad'),
            rol=row.get('rol', 'user'),
        )

    def is_authenticated(self, session: dict) -> bool:
        return self.get_usuario_actual(session) is not None

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def login(self, username: str, password: str, session: dict) -> Optional[Usuario]:
        """Valida credenciales y guarda user_id en session.

        Acepta username o email en el campo `username`.
        Retorna el Usuario si el login es exitoso, None si falla.
        """
        if not self._db:
            return None
        identifier = username.strip()
        # Intentar por username; si falla y tiene @, intentar por email
        row = self._db.get_user_by_username(identifier)
        if not row and '@' in identifier:
            row = self._db.get_user_by_email(identifier)
        if not row:
            return None
        if not self._check_password(password, row['password_hash']):
            return None
        session['user_id'] = row['id']
        return Usuario(
            id=row['id'],
            username=row['username'],
            email=row.get('email'),
            edad=row.get('edad'),
            rol=row.get('rol', 'user'),
        )

    def logout(self, session: dict) -> None:
        """Limpia completamente la session del usuario."""
        session.clear()

    def register(self, username: str, password: str, edad: Optional[int] = None, email: Optional[str] = None, rol: str = 'user') -> Optional[Usuario]:
        """Crea un nuevo usuario.

        Retorna el Usuario creado, o None si el username ya existe o hay error.
        """
        if not self._db:
            return None
        username = username.strip()
        if not username or not password:
            return None
        if self._db.get_user_by_username(username):
            return None  # username ya en uso
        pw_hash = self._hash_password(password)
        row = self._db.create_user(username, pw_hash, edad, email=email, rol=rol)
        if not row:
            return None
        return Usuario(
            id=row['id'],
            username=row['username'],
            email=row.get('email'),
            edad=row.get('edad'),
            rol=row.get('rol', 'user'),
        )

    # ------------------------------------------------------------------
    # JWT
    # ------------------------------------------------------------------

    def generate_token(self, usuario: 'Usuario') -> Optional[str]:
        """Genera un JWT para el usuario dado. Retorna None si PyJWT no esta disponible."""
        if not _JWT_AVAILABLE:
            return None
        payload = {
            'sub': str(usuario.id),
            'username': usuario.username,
            'rol': usuario.rol,
            'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=_JWT_EXPIRY_HOURS),
        }
        return pyjwt.encode(payload, self._jwt_secret, algorithm=_JWT_ALGORITHM)

    def verify_token(self, token: str) -> Optional['Usuario']:
        """Verifica un JWT y retorna el Usuario, o None si es invalido/expirado."""
        if not _JWT_AVAILABLE or not token:
            return None
        try:
            payload = pyjwt.decode(token, self._jwt_secret, algorithms=[_JWT_ALGORITHM])
        except pyjwt.ExpiredSignatureError:
            return None
        except pyjwt.InvalidTokenError:
            return None
        user_id_str = payload.get('sub')
        if user_id_str is None:
            return None
        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            return None
        if self._db:
            row = self._db.get_user_by_id(user_id)
            if not row:
                return None
            return Usuario(
                id=row['id'],
                username=row['username'],
                email=row.get('email'),
                edad=row.get('edad'),
                rol=row.get('rol', 'user'),
            )
        # Sin DB: construir desde payload (modo degradado)
        return Usuario(
            id=user_id,
            username=payload.get('username', ''),
            edad=None,
            rol=payload.get('rol', 'user'),
        )


    # ------------------------------------------------------------------
    # Helpers de password
    # ------------------------------------------------------------------

    @staticmethod
    def _hash_password(password: str) -> str:
        if not _BCRYPT_AVAILABLE:
            raise RuntimeError("bcrypt no instalado. Ejecuta: pip install bcrypt")
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    @staticmethod
    def _check_password(password: str, pw_hash: str) -> bool:
        if not _BCRYPT_AVAILABLE:
            return False
        try:
            return bcrypt.checkpw(password.encode('utf-8'), pw_hash.encode('utf-8'))
        except Exception:
            logger.error('Error al verificar password hash', exc_info=True)
            return False
