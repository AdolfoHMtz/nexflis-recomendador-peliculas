"""Tests unitarios para JWT en AuthService."""
import unittest
from unittest.mock import MagicMock

from services.auth_service import AuthService
from models.usuario import Usuario


class TestAuthJWT(unittest.TestCase):

    def setUp(self):
        self.auth = AuthService(db_service=None, jwt_secret='test_secret_12345')
        self.usuario = Usuario(id=42, username='testuser', edad=25, rol='user')

    def test_generate_token_returns_string(self):
        token = self.auth.generate_token(self.usuario)
        self.assertIsNotNone(token)
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 10)

    def test_verify_token_valid(self):
        token = self.auth.generate_token(self.usuario)
        result = self.auth.verify_token(token)
        self.assertIsNotNone(result)
        self.assertEqual(result.id, 42)
        self.assertEqual(result.username, 'testuser')
        self.assertEqual(result.rol, 'user')

    def test_verify_token_invalid(self):
        result = self.auth.verify_token('token.invalido.aqui')
        self.assertIsNone(result)

    def test_verify_token_empty(self):
        result = self.auth.verify_token('')
        self.assertIsNone(result)

    def test_verify_token_wrong_secret(self):
        other_auth = AuthService(db_service=None, jwt_secret='otro_secreto')
        token = other_auth.generate_token(self.usuario)
        result = self.auth.verify_token(token)
        self.assertIsNone(result)

    def test_verify_token_with_db(self):
        mock_db = MagicMock()
        mock_db.get_user_by_id.return_value = {
            'id': 42, 'username': 'testuser', 'edad': 25, 'rol': 'user'
        }
        auth_with_db = AuthService(db_service=mock_db, jwt_secret='test_secret_12345')
        token = auth_with_db.generate_token(self.usuario)
        result = auth_with_db.verify_token(token)
        self.assertIsNotNone(result)
        self.assertEqual(result.id, 42)
        mock_db.get_user_by_id.assert_called_once_with(42)

    def test_verify_token_user_not_found_in_db(self):
        mock_db = MagicMock()
        mock_db.get_user_by_id.return_value = None
        auth_with_db = AuthService(db_service=mock_db, jwt_secret='test_secret_12345')
        token = auth_with_db.generate_token(self.usuario)
        result = auth_with_db.verify_token(token)
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
