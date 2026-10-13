"""
Pruebas E2E - Fase 1.

Levanta la app Flask con test_client(). Mockea TMDB y DB para no
requerir servicios externos. Verifica contratos HTTP de todas las rutas.
"""
import json
import unittest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Fabrica de app de prueba
# ---------------------------------------------------------------------------

def _make_app():
    """Crea una instancia Flask con servicios mockeados."""
    import os
    os.environ.setdefault('JWT_SECRET', 'test_e2e_secret_32bytes_xxxxxxxxx')

    # Importaciones diferidas para que los patches ya esten activos
    from services.db_service import DatabaseService
    from services.tmdb_service import TmdbService
    from services.auth_service import AuthService
    from core.motor_recomendacion import MotorRecomendacion
    from core.motor_explicacion import MotorExplicacion
    from routes import busqueda_routes, recomendacion_routes, auth_routes

    from flask import Flask
    app = Flask(__name__, template_folder='../templates')
    app.secret_key = 'test_secret'
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    # Registra csrf_token() como global de Jinja para renderizar los formularios
    from flask_wtf.csrf import CSRFProtect
    CSRFProtect(app)

    # DB mock — siempre ready, usuarios en memoria
    db = MagicMock(spec=DatabaseService)
    db.is_ready.return_value = True
    db.cache_get.return_value = None
    db.cache_set.return_value = None
    db.upsert_pelicula_clasificacion.return_value = None
    db.get_clasificacion_edad.return_value = None
    db.get_user_by_username.return_value = None
    db.get_user_by_id.return_value = None
    db.create_user.return_value = None
    db.get_user_by_email.return_value = None
    db.get_plan_usuario.return_value = {'plan': 'free', 'plan_expires_at': None}

    # TMDB mock — deshabilitado por defecto
    tmdb = MagicMock(spec=TmdbService)
    tmdb.is_ready.return_value = False
    tmdb.search_movies.return_value = []
    tmdb.get_popular.return_value = []
    tmdb.enrich_movies.return_value = []
    tmdb.get_movie_details.return_value = {
        'id': 1, 'title': 'Test Movie', 'genres_list': [], 'keywords_list': [],
        'cast_list': [], 'director': '', 'runtime': 90, 'vote_average': 7.0,
        'overview': 'Test overview', 'poster_path': '', 'adult': False,
        'clasificacion_edad': 0, 'collection_id': 0, 'collection_name': '',
        'recommendations': [], 'similar': [],
    }
    tmdb.hero_search.return_value = {'fallback': True, 'results': []}
    tmdb.get_dimension_options.return_value = []
    tmdb.recommend_from_history.return_value = []

    motor = MotorRecomendacion()
    explicador = MotorExplicacion()
    auth = AuthService(db_service=db, jwt_secret=os.environ['JWT_SECRET'])

    busqueda_routes.register(app, tmdb)
    recomendacion_routes.register(app, tmdb, motor, explicador, auth_service=auth)
    auth_routes.register(app, auth)

    @app.route('/')
    def index():
        from flask import render_template, session
        usuario = auth.get_usuario_actual(session)
        return render_template(
            'index.html',
            top_10=[], recomendados=[], recomendados_sec=[],
            tipo_sec='', historial=[], ultima_peli=None, usuario=usuario,
        )

    app._test_db = db
    app._test_tmdb = tmdb
    app._test_auth = auth
    return app


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class E2EBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _make_app()
        cls.client = cls.app.test_client()
        cls.db = cls.app._test_db
        cls.tmdb = cls.app._test_tmdb
        cls.auth = cls.app._test_auth

    def _json_post(self, url, data):
        return self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json',
        )

    def _auth_header(self, token):
        return {'Authorization': f'Bearer {token}'}


# ---------------------------------------------------------------------------
# Rutas generales
# ---------------------------------------------------------------------------

class TestIndex(E2EBase):
    def test_index_200(self):
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)


# ---------------------------------------------------------------------------
# Busqueda
# ---------------------------------------------------------------------------

class TestBusqueda(E2EBase):
    def test_buscar_tmdb_disabled_devuelve_lista_vacia(self):
        r = self.client.get('/api/buscar?q=batman')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json(), [])

    def test_buscar_tmdb_enabled_retorna_resultados(self):
        self.tmdb.is_ready.return_value = True
        self.tmdb.search_movies.return_value = [
            {'id': 1, 'title': 'Batman', 'genres_list': [], 'keywords_list': [],
             'cast_list': [], 'director': '', 'runtime': 0, 'vote_average': 0,
             'overview': '', 'poster_path': ''},
        ]
        self.tmdb.enrich_movies.return_value = self.tmdb.search_movies.return_value
        r = self.client.get('/api/buscar?q=batman')
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIsInstance(data, list)
        self.tmdb.is_ready.return_value = False

    def test_buscar_query_corta_devuelve_vacio(self):
        r = self.client.get('/api/buscar?q=a')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json(), [])

    def test_hero_search_tmdb_disabled(self):
        r = self._json_post('/api/hero/search', {'selected': {}, 'logicMode': 'and'})
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn('results', data)

    def test_hero_options_tmdb_disabled(self):
        r = self.client.get('/api/hero/options?dimension=genre&q=accion')
        self.assertEqual(r.status_code, 200)

    def test_movie_details_tmdb_disabled(self):
        r = self.client.get('/api/movie/1')
        self.assertEqual(r.status_code, 503)

    def test_movie_details_tmdb_enabled(self):
        self.tmdb.is_ready.return_value = True
        r = self.client.get('/api/movie/1')
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data['id'], 1)
        self.tmdb.is_ready.return_value = False


# ---------------------------------------------------------------------------
# Auth web (session)
# ---------------------------------------------------------------------------

class TestAuthWeb(E2EBase):
    def test_login_form_200(self):
        r = self.client.get('/auth/login')
        self.assertEqual(r.status_code, 200)

    def test_register_form_200(self):
        r = self.client.get('/auth/register')
        self.assertEqual(r.status_code, 200)

    def test_login_post_campos_vacios_400(self):
        r = self.client.post('/auth/login', data={'username': '', 'password': ''})
        self.assertEqual(r.status_code, 400)

    def test_login_post_credenciales_invalidas_401(self):
        self.db.get_user_by_username.return_value = None
        r = self.client.post('/auth/login', data={'username': 'noexiste', 'password': 'pass'})
        self.assertEqual(r.status_code, 401)

    def test_register_post_passwords_no_coinciden_400(self):
        r = self.client.post('/auth/register', data={
            'username': 'user1', 'password': 'abc123', 'confirm_password': 'xyz999'
        })
        self.assertEqual(r.status_code, 400)

    def test_register_post_password_corta_400(self):
        r = self.client.post('/auth/register', data={
            'username': 'user1', 'password': 'abc', 'confirm_password': 'abc'
        })
        self.assertEqual(r.status_code, 400)

    def test_register_post_username_en_uso_409(self):
        self.db.get_user_by_username.return_value = {
            'id': 1, 'username': 'user1', 'password_hash': 'x', 'edad': None, 'rol': 'user'
        }
        r = self.client.post('/auth/register', data={
            'username': 'user1', 'password': 'secreta123', 'confirm_password': 'secreta123'
        })
        self.assertEqual(r.status_code, 409)
        self.db.get_user_by_username.return_value = None

    def test_logout_post_redirige(self):
        r = self.client.post('/auth/logout')
        self.assertIn(r.status_code, (302, 200))


# ---------------------------------------------------------------------------
# Auth API JSON (JWT)
# ---------------------------------------------------------------------------

class TestAuthAPI(E2EBase):
    def test_api_me_sin_token_no_autenticado(self):
        r = self.client.get('/api/auth/me')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.get_json()['authenticated'])

    def test_api_login_campos_vacios_400(self):
        r = self._json_post('/api/auth/login', {'username': '', 'password': ''})
        self.assertEqual(r.status_code, 400)

    def test_api_login_credenciales_invalidas_401(self):
        self.db.get_user_by_username.return_value = None
        r = self._json_post('/api/auth/login', {'username': 'noexiste', 'password': 'pass'})
        self.assertEqual(r.status_code, 401)

    def test_api_login_exitoso_devuelve_token(self):
        import bcrypt
        pw_hash = bcrypt.hashpw(b'secreta123', bcrypt.gensalt()).decode()
        self.db.get_user_by_username.return_value = {
            'id': 10, 'username': 'juanito', 'password_hash': pw_hash, 'edad': 30, 'rol': 'user'
        }
        r = self._json_post('/api/auth/login', {'username': 'juanito', 'password': 'secreta123'})
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn('token', data)
        self.assertIsNotNone(data['token'])
        self.db.get_user_by_username.return_value = None

    def test_api_me_con_token_valido(self):
        from models.usuario import Usuario
        usuario = Usuario(id=10, username='juanito', edad=30, rol='user')
        token = self.auth.generate_token(usuario)
        self.db.get_user_by_id.return_value = {
            'id': 10, 'username': 'juanito', 'edad': 30, 'rol': 'user'
        }
        r = self.client.get('/api/auth/me', headers=self._auth_header(token))
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data['authenticated'])
        self.assertEqual(data['username'], 'juanito')
        self.db.get_user_by_id.return_value = None

    def test_api_me_token_invalido_no_autenticado(self):
        r = self.client.get('/api/auth/me', headers=self._auth_header('token.malo.aqui'))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.get_json()['authenticated'])

    def test_api_register_exitoso_201(self):
        self.db.get_user_by_username.return_value = None
        self.db.create_user.return_value = {
            'id': 20, 'username': 'nuevo', 'edad': 25, 'rol': 'user'
        }
        r = self._json_post('/api/auth/register', {
            'username': 'nuevo', 'password': 'secreta123', 'edad': 25
        })
        self.assertEqual(r.status_code, 201)
        data = r.get_json()
        self.assertIn('token', data)
        self.db.create_user.return_value = None

    def test_api_register_username_en_uso_409(self):
        self.db.get_user_by_username.return_value = {
            'id': 1, 'username': 'nuevo', 'password_hash': 'x', 'edad': None, 'rol': 'user'
        }
        r = self._json_post('/api/auth/register', {
            'username': 'nuevo', 'password': 'secreta123', 'edad': 25
        })
        self.assertEqual(r.status_code, 409)
        self.db.get_user_by_username.return_value = None

    def test_api_register_password_corta_400(self):
        r = self._json_post('/api/auth/register', {'username': 'x', 'password': 'abc'})
        self.assertEqual(r.status_code, 400)

    def test_api_logout_200(self):
        r = self._json_post('/api/auth/logout', {})
        self.assertEqual(r.status_code, 200)
        self.assertIn('message', r.get_json())


# ---------------------------------------------------------------------------
# Perfil de usuario
# ---------------------------------------------------------------------------

class TestPerfilUsuario(E2EBase):
    def _token_para(self, user_id=10, username='juanito', edad=30):
        from models.usuario import Usuario
        u = Usuario(id=user_id, username=username, edad=edad, rol='user')
        return self.auth.generate_token(u)

    def test_get_perfil_sin_token_401(self):
        r = self.client.get('/api/users/me')
        self.assertEqual(r.status_code, 401)

    def test_get_perfil_con_token_200(self):
        token = self._token_para()
        self.db.get_user_by_id.return_value = {
            'id': 10, 'username': 'juanito', 'edad': 30, 'rol': 'user'
        }
        r = self.client.get('/api/users/me', headers=self._auth_header(token))
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data['username'], 'juanito')
        self.db.get_user_by_id.return_value = None

    def test_patch_perfil_sin_token_401(self):
        r = self._json_post('/api/users/me', {'edad': 25})
        # POST no es PATCH, pero verify que sin token da 401
        r2 = self.client.patch(
            '/api/users/me',
            data=json.dumps({'edad': 25}),
            content_type='application/json',
        )
        self.assertEqual(r2.status_code, 401)

    def test_patch_perfil_actualiza_edad(self):
        token = self._token_para()
        self.db.get_user_by_id.return_value = {
            'id': 10, 'username': 'juanito', 'edad': 30, 'rol': 'user'
        }
        self.db.update_user.return_value = {
            'id': 10, 'username': 'juanito', 'edad': 25, 'rol': 'user'
        }
        import bcrypt
        pw_hash = bcrypt.hashpw(b'secreta123', bcrypt.gensalt()).decode()
        self.db.get_user_by_id.return_value['password_hash'] = pw_hash
        r = self.client.patch(
            '/api/users/me',
            data=json.dumps({'edad': 25, 'password_actual': 'secreta123'}),
            content_type='application/json',
            headers=self._auth_header(token),
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()['edad'], 25)
        self.db.get_user_by_id.return_value = None
        self.db.update_user.return_value = None

    def test_patch_perfil_edad_invalida_400(self):
        token = self._token_para()
        self.db.get_user_by_id.return_value = {
            'id': 10, 'username': 'juanito', 'edad': 30, 'rol': 'user'
        }
        r = self.client.patch(
            '/api/users/me',
            data=json.dumps({'edad': 999}),
            content_type='application/json',
            headers=self._auth_header(token),
        )
        self.assertEqual(r.status_code, 400)
        self.db.get_user_by_id.return_value = None

    def test_patch_perfil_password_corta_400(self):
        token = self._token_para()
        self.db.get_user_by_id.return_value = {
            'id': 10, 'username': 'juanito', 'edad': 30, 'rol': 'user'
        }
        r = self.client.patch(
            '/api/users/me',
            data=json.dumps({'password': 'abc'}),
            content_type='application/json',
            headers=self._auth_header(token),
        )
        self.assertEqual(r.status_code, 400)
        self.db.get_user_by_id.return_value = None

    def test_patch_perfil_body_vacio_400(self):
        token = self._token_para()
        self.db.get_user_by_id.return_value = {
            'id': 10, 'username': 'juanito', 'edad': 30, 'rol': 'user'
        }
        r = self.client.patch(
            '/api/users/me',
            data=json.dumps({}),
            content_type='application/json',
            headers=self._auth_header(token),
        )
        self.assertEqual(r.status_code, 400)
        self.db.get_user_by_id.return_value = None


# ---------------------------------------------------------------------------
# Recomendacion
# ---------------------------------------------------------------------------

class TestRecomendacion(E2EBase):
    def test_recomendar_tmdb_disabled_redirige(self):
        self.tmdb.is_ready.return_value = False
        r = self.client.post('/recomendar', data={
            'titulo': 'Batman', 'movie_id': '', 'minutos': '60', 'reaccion': 'like'
        })
        self.assertIn(r.status_code, (302, 200))

    def test_recomendar_tmdb_enabled_movie_no_encontrada_redirige(self):
        self.tmdb.is_ready.return_value = True
        self.tmdb.search_movies.return_value = []
        r = self.client.post('/recomendar', data={
            'titulo': 'Pelicula Inexistente XYZ', 'movie_id': '', 'minutos': '0', 'reaccion': 'like'
        })
        self.assertEqual(r.status_code, 302)
        self.tmdb.is_ready.return_value = False

    def test_recomendar_tmdb_enabled_con_movie_id(self):
        self.tmdb.is_ready.return_value = True
        self.tmdb.recommend_from_history.return_value = []
        self.tmdb.enrich_movies.return_value = []
        self.tmdb.get_popular.return_value = []
        r = self.client.post('/recomendar', data={
            'titulo': '', 'movie_id': '1', 'minutos': '45', 'reaccion': 'like'
        })
        self.assertIn(r.status_code, (200, 302))
        self.tmdb.is_ready.return_value = False


if __name__ == '__main__':
    unittest.main()
