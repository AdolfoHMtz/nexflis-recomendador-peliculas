"""
crypto_utils.py — Helpers criptográficos compartidos entre servicios.

Hace la derivación de clave AES-256 (Fernet) y el secreto HMAC
para que payment_service e historial_export_service usen exactamente
la misma clave sin duplicar lógica.
"""
import hashlib
import os
from base64 import b64encode

from cryptography.fernet import Fernet


def get_fernet() -> Fernet:
    """Deriva una clave AES-256 de FLASK_SECRET_KEY y retorna instancia Fernet."""
    secret = os.getenv('FLASK_SECRET_KEY', 'nexflis_flask_secret_changeme_in_prod')
    key_bytes = hashlib.sha256(secret.encode()).digest()
    fernet_key = b64encode(key_bytes)
    return Fernet(fernet_key)


def get_hmac_secret() -> bytes:
    """Retorna el secreto HMAC desde JWT_SECRET."""
    secret = os.getenv('JWT_SECRET', 'nexflis_jwt_secret_changeme_in_prod')
    return secret.encode('utf-8')
