"""Tests para clasificacion de edad persistida (Fase 2)."""
import unittest
from unittest.mock import MagicMock, patch, call


class TestDbServiceClasificacion(unittest.TestCase):
    """Prueba los metodos de clasificacion de edad en DatabaseService sin conexion real."""

    def _make_service(self):
        from services.db_service import DatabaseService
        svc = DatabaseService.__new__(DatabaseService)
        svc._db_url = ''
        svc._ready = False
        return svc

    def test_upsert_no_op_when_not_ready(self):
        svc = self._make_service()
        # No debe lanzar excepcion; simplemente retorna sin hacer nada
        svc.upsert_pelicula_clasificacion(1, 'Test', 0, False)

    def test_get_clasificacion_edad_returns_none_when_not_ready(self):
        svc = self._make_service()
        result = svc.get_clasificacion_edad(1)
        self.assertIsNone(result)

    def test_upsert_calls_execute_with_correct_params(self):
        from services.db_service import DatabaseService
        svc = self._make_service()
        svc._ready = True

        mock_cur = MagicMock()
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        svc._connect = MagicMock(return_value=mock_conn)
        svc.upsert_pelicula_clasificacion(42, 'Pelicula Test', 18, True)

        mock_cur.execute.assert_called_once()
        args = mock_cur.execute.call_args[0]
        self.assertIn('INSERT INTO peliculas', args[0])
        self.assertEqual(args[1], (42, 'Pelicula Test', 18, True))


class TestFiltrarPorEdad(unittest.TestCase):
    """Prueba la logica de _filtrar_por_edad en recomendacion_routes."""

    def _make_items(self):
        return [
            {'id': 1, 'title': 'Apta', 'clasificacion_edad': 0, 'adult': False},
            {'id': 2, 'title': 'Adultos', 'clasificacion_edad': 18, 'adult': True},
            {'id': 3, 'title': 'Mayores 13', 'clasificacion_edad': 13, 'adult': False},
            {'id': 4, 'title': 'Solo adult flag', 'adult': True},  # sin clasificacion_edad
        ]

    def _patch_globals(self, auth_mock, session_mock):
        import routes.recomendacion_routes as rr
        rr._auth = auth_mock
        return rr

    def test_sin_usuario_devuelve_todo(self):
        from models.usuario import Usuario
        import routes.recomendacion_routes as rr

        auth = MagicMock()
        auth.get_usuario_actual.return_value = None
        rr._auth = auth

        items = self._make_items()
        with patch('routes.recomendacion_routes.session', {}):
            result = rr._filtrar_por_edad(items)
        self.assertEqual(len(result), 4)

    def test_usuario_mayor_de_edad_devuelve_todo(self):
        from models.usuario import Usuario
        import routes.recomendacion_routes as rr

        usuario = Usuario(id=1, username='adulto', edad=25, rol='user')
        auth = MagicMock()
        auth.get_usuario_actual.return_value = usuario
        rr._auth = auth

        items = self._make_items()
        with patch('routes.recomendacion_routes.session', {}):
            result = rr._filtrar_por_edad(items)
        self.assertEqual(len(result), 4)

    def test_usuario_menor_filtra_clasificacion_edad_18(self):
        from models.usuario import Usuario
        import routes.recomendacion_routes as rr

        usuario = Usuario(id=2, username='menor', edad=15, rol='user')
        auth = MagicMock()
        auth.get_usuario_actual.return_value = usuario
        rr._auth = auth

        items = self._make_items()
        with patch('routes.recomendacion_routes.session', {}):
            result = rr._filtrar_por_edad(items)

        ids = [r['id'] for r in result]
        self.assertIn(1, ids)       # apta todo publico
        self.assertNotIn(2, ids)    # clasificacion_edad=18 bloqueada
        self.assertIn(3, ids)       # clasificacion_edad=13, usuario tiene 15 -> permitida
        self.assertNotIn(4, ids)    # adult=True fallback -> bloqueada

    def test_usuario_sin_edad_bloquea_contenido_18(self):
        """Sin edad registrada se bloquea +18/adult por precaucion (no se filtra el resto)."""
        from models.usuario import Usuario
        import routes.recomendacion_routes as rr

        usuario = Usuario(id=3, username='sinedad', edad=None, rol='user')
        auth = MagicMock()
        auth.get_usuario_actual.return_value = usuario
        rr._auth = auth

        items = self._make_items()
        with patch('routes.recomendacion_routes.session', {}):
            result = rr._filtrar_por_edad(items)
        ids = [r['id'] for r in result]
        self.assertEqual(sorted(ids), [1, 3])


if __name__ == '__main__':
    unittest.main()
