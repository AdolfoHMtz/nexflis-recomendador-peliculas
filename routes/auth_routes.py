"""
auth_routes - Fase 2.

Endpoints web (session):
  GET  /auth/login      -> formulario de login
  POST /auth/login      -> procesa login
  GET  /auth/register   -> formulario de registro
  POST /auth/register   -> procesa registro
  POST /auth/logout     -> cierra sesion

Endpoints API JSON (JWT):
  GET  /api/auth/me       -> usuario actual (session o Bearer token)
  POST /api/auth/login    -> devuelve JWT
  POST /api/auth/register -> crea usuario y devuelve JWT
  POST /api/auth/logout   -> (stateless; confirma logout al cliente)
"""
from flask import (
    Blueprint, jsonify, redirect, render_template,
    request, session, url_for, flash
)

from extensions import limiter
from services.auth_service import AuthService
from routes.jwt_middleware import init_jwt_middleware, jwt_required

bp = Blueprint('auth', __name__)
_auth: AuthService = None


def register(app, auth_service: AuthService = None, limiter=None, csrf=None):
    """Registra las rutas de autenticacion en la app Flask."""
    global _auth
    _auth = auth_service
    init_jwt_middleware(auth_service)
    if csrf:
        # Los endpoints JSON /api/* no usan formularios HTML → excluir de CSRF
        # (protegidos por SameSite=Lax + Content-Type: application/json)
        csrf.exempt(api_login)
        csrf.exempt(api_register)
        csrf.exempt(api_logout)
        csrf.exempt(api_me)
        csrf.exempt(api_usuario_ultima_consulta)
        csrf.exempt(api_usuario_historial)
        csrf.exempt(api_users_me_get)
        csrf.exempt(api_users_me_patch)
    app.register_blueprint(bp)


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@bp.route('/auth/login', methods=['GET'])
def login_form():
    if _auth and _auth.is_authenticated(session):
        return redirect(url_for('index'))
    return render_template('auth/login.html')


@bp.route('/auth/login', methods=['POST'])
@limiter.limit('10 per minute')
def login_post():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    if not username or not password:
        flash('Usuario y contraseña son obligatorios.', 'error')
        return render_template('auth/login.html'), 400

    if not _auth:
        flash('Autenticacion no disponible (sin base de datos).', 'error')
        return render_template('auth/login.html'), 503

    usuario = _auth.login(username, password, session)
    if not usuario:
        flash('Usuario o contraseña incorrectos.', 'error')
        return render_template('auth/login.html'), 401

    return redirect(url_for('index'))


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

@bp.route('/auth/register', methods=['GET'])
def register_form():
    if _auth and _auth.is_authenticated(session):
        return redirect(url_for('index'))
    return render_template('auth/register.html')


@bp.route('/auth/register', methods=['POST'])
@limiter.limit('5 per minute')
def register_post():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    confirm  = request.form.get('confirm_password', '')
    edad_raw = request.form.get('edad', '').strip()

    if not username or not password:
        flash('Usuario y contraseña son obligatorios.', 'error')
        return render_template('auth/register.html'), 400

    if password != confirm:
        flash('Las contraseñas no coinciden.', 'error')
        return render_template('auth/register.html'), 400

    if len(password) < 6:
        flash('La contraseña debe tener al menos 6 caracteres.', 'error')
        return render_template('auth/register.html'), 400

    edad = None
    if edad_raw:
        try:
            edad = int(edad_raw)
            if edad < 0 or edad > 120:
                raise ValueError
        except ValueError:
            flash('Edad invalida.', 'error')
            return render_template('auth/register.html'), 400

    if not _auth:
        flash('Registro no disponible (sin base de datos).', 'error')
        return render_template('auth/register.html'), 503

    usuario = _auth.register(username, password, edad=edad)
    if not usuario:
        flash('El nombre de usuario ya esta en uso.', 'error')
        return render_template('auth/register.html'), 409

    # Auto-login tras registro exitoso
    _auth.login(username, password, session)
    return redirect(url_for('index'))


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

@bp.route('/auth/logout', methods=['POST'])
def logout():
    if _auth:
        _auth.logout(session)
    return redirect(url_for('index'))


# ---------------------------------------------------------------------------
# API JSON
# ---------------------------------------------------------------------------

@bp.route('/api/auth/me', methods=['GET'])
def api_me():
    """Retorna el usuario actual. Acepta session o Bearer token."""
    if not _auth:
        return jsonify({'authenticated': False}), 200
    # Primero intenta JWT
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[len('Bearer '):]
        usuario = _auth.verify_token(token)
    else:
        usuario = _auth.get_usuario_actual(session)
    if not usuario:
        return jsonify({'authenticated': False}), 200
    # Completar email desde BD si no viene en el objeto Usuario
    email = getattr(usuario, 'email', None)
    if email is None and _auth and _auth._db:
        fila = _auth._db.get_user_by_id(usuario.id)
        if fila:
            email = fila.get('email')
    plan_info = {}
    if _auth and _auth._db:
        plan_info = _auth._db.get_plan_usuario(usuario.id)
    return jsonify({
        'authenticated':   True,
        'id':              usuario.id,
        'username':        usuario.username,
        'email':           email,
        'edad':            usuario.edad,
        'rol':             usuario.rol,
        'needs_age':       usuario.edad is None,
        'plan':            plan_info.get('plan', 'free'),
        'plan_expires_at': plan_info.get('plan_expires_at'),
    })


@bp.route('/api/auth/login', methods=['POST'])
@limiter.limit('10 per minute')
def api_login():
    """Login via JSON. Retorna JWT si las credenciales son validas.

    Body: {"username": "...", "password": "..."}
    """
    if not _auth:
        return jsonify({'error': 'Auth no disponible'}), 503

    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': 'username y password son obligatorios'}), 400

    usuario = _auth.login(username, password, session)
    if not usuario:
        return jsonify({'error': 'Credenciales invalidas'}), 401

    token = _auth.generate_token(usuario)
    plan_info = _auth._db.get_plan_usuario(usuario.id) if _auth._db else {}
    return jsonify({
        'token': token,
        'user': {
            'id':              usuario.id,
            'username':        usuario.username,
            'email':           usuario.email,
            'edad':            usuario.edad,
            'rol':             usuario.rol,
            'needs_age':       usuario.edad is None,
            'plan':            plan_info.get('plan', 'free'),
            'plan_expires_at': plan_info.get('plan_expires_at'),
        }
    })


@bp.route('/api/auth/register', methods=['POST'])
@limiter.limit('5 per minute')
def api_register():
    """Registro via JSON. Retorna JWT si el registro es exitoso.

    Body: {"username": "...", "password": "...", "edad": 25}
    """
    if not _auth:
        return jsonify({'error': 'Auth no disponible'}), 503

    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    edad_raw = data.get('edad')
    email    = data.get('email', '').strip() or None

    if not username or not password:
        return jsonify({'error': 'username y password son obligatorios'}), 400

    if len(password) < 6:
        return jsonify({'error': 'La contrasena debe tener al menos 6 caracteres'}), 400

    if edad_raw is None:
        return jsonify({'error': 'La edad es obligatoria'}), 400

    edad = None
    try:
        edad = int(edad_raw)
        if edad < 0 or edad > 120:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({'error': 'Edad invalida (0-120)'}), 400

    # Verificar email duplicado antes de intentar registro
    if email and _auth._db and _auth._db.get_user_by_email(email):
        return jsonify({'error': 'El correo ya está registrado'}), 409

    usuario = _auth.register(username, password, edad=edad, email=email)
    if not usuario:
        return jsonify({'error': 'El nombre de usuario ya esta en uso'}), 409

    _auth.login(username, password, session)
    token = _auth.generate_token(usuario)
    return jsonify({
        'token': token,
        'user': {
            'id':        usuario.id,
            'username':  usuario.username,
            'email':     usuario.email,
            'edad':      usuario.edad,
            'rol':       usuario.rol,
            'needs_age': usuario.edad is None,
        }
    }), 201


@bp.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """Logout via API. Borra la session del servidor (JWT es stateless en el cliente)."""
    if _auth:
        _auth.logout(session)
    return jsonify({'message': 'Sesion cerrada'}), 200


# ---------------------------------------------------------------------------
# Perfil de usuario
# ---------------------------------------------------------------------------

@bp.route('/api/usuario/ultima-consulta', methods=['GET'])
@jwt_required
def api_usuario_ultima_consulta(usuario):
    """Devuelve la última respuesta de recomendación persistida del usuario."""
    if not _auth or not _auth._db:
        return jsonify(None), 200
    consulta = _auth._db.obtener_ultima_consulta(usuario.id)
    return jsonify(consulta), 200


@bp.route('/api/usuario/historial', methods=['GET'])
@jwt_required
def api_usuario_historial(usuario):
    """Devuelve el historial persistido en BD del usuario autenticado."""
    if not _auth or not _auth._db:
        return jsonify([]), 200
    historial = _auth._db.obtener_historial_usuario(usuario.id, limit=20)
    return jsonify(historial), 200


@bp.route('/api/users/me', methods=['GET'])
@jwt_required
def api_users_me_get(usuario):
    """Retorna el perfil completo del usuario autenticado via JWT."""
    # Buscar email desde BD (Usuario dataclass no siempre lo trae)
    email = getattr(usuario, 'email', None)
    if email is None and _auth and _auth._db:
        fila = _auth._db.get_user_by_id(usuario.id)
        if fila:
            email = fila.get('email')
    return jsonify({
        'id':       usuario.id,
        'username': usuario.username,
        'email':    email,
        'edad':     usuario.edad,
        'rol':      usuario.rol,
    })


@bp.route('/api/users/me', methods=['DELETE'])
@jwt_required
def api_users_me_delete(usuario):
    """Elimina la cuenta del usuario autenticado. Requiere contraseña actual."""
    if not _auth or not _auth._db:
        return jsonify({'error': 'DB no disponible'}), 503

    data = request.get_json(silent=True) or {}
    pw_actual = str(data.get('password_actual', '')).strip()
    if not pw_actual:
        return jsonify({'error': 'La contraseña es requerida para eliminar la cuenta'}), 400

    fila = _auth._db.get_user_by_id(usuario.id)
    if not fila or not _auth._check_password(pw_actual, fila['password_hash']):
        return jsonify({'error': 'Contraseña incorrecta'}), 401

    ok = _auth._db.eliminar_usuario(usuario.id)
    if not ok:
        return jsonify({'error': 'No se pudo eliminar la cuenta'}), 500

    _auth.logout(session)
    return jsonify({'mensaje': 'Cuenta eliminada correctamente'}), 200


@bp.route('/api/users/me', methods=['PATCH'])
@jwt_required
def api_users_me_patch(usuario):
    """Actualiza el perfil del usuario autenticado.

    Campos aceptados: edad (int), password (str, min 6 chars), email (str),
    username (str, min 3 chars), password_actual (str, requerido para cambiar password).
    Body JSON: {"edad": 25, "email": "...", "username": "...", "password": "...", "password_actual": "..."}
    """
    if not _auth or not _auth._db:
        return jsonify({'error': 'DB no disponible'}), 503

    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({'error': 'Body JSON requerido'}), 400

    # Verificar contraseña actual SIEMPRE, para cualquier cambio
    pw_actual = str(data.get('password_actual', '')).strip()
    if not pw_actual:
        return jsonify({'error': 'La contraseña actual es requerida para cualquier cambio'}), 400
    fila_user = _auth._db.get_user_by_id(usuario.id)
    if not fila_user or not _auth._check_password(pw_actual, fila_user['password_hash']):
        return jsonify({'error': 'Contraseña actual incorrecta'}), 401

    nueva_edad = None
    nuevo_hash = None
    nuevo_email = None
    nuevo_username = None

    if 'edad' in data:
        try:
            nueva_edad = int(data['edad'])
            if nueva_edad < 0 or nueva_edad > 120:
                raise ValueError
        except (ValueError, TypeError):
            return jsonify({'error': 'Edad invalida'}), 400

    if 'email' in data:
        nuevo_email = str(data['email']).strip()
        if nuevo_email and '@' not in nuevo_email:
            return jsonify({'error': 'Email invalido'}), 400

    if 'username' in data:
        nuevo_username = str(data['username']).strip()
        if len(nuevo_username) < 3:
            return jsonify({'error': 'El username debe tener al menos 3 caracteres'}), 400

    if 'password' in data:
        nueva_pw = str(data['password'])
        if len(nueva_pw) < 6:
            return jsonify({'error': 'La contrasena debe tener al menos 6 caracteres'}), 400
        nuevo_hash = _auth._hash_password(nueva_pw)

    if nueva_edad is None and nuevo_hash is None and nuevo_email is None and nuevo_username is None:
        return jsonify({'error': 'Nada que actualizar. Campos validos: edad, email, username, password'}), 400

    row = _auth._db.update_user(
        usuario.id,
        edad=nueva_edad,
        password_hash=nuevo_hash,
        email=nuevo_email,
        username=nuevo_username,
    )
    if not row:
        return jsonify({'error': 'No se pudo actualizar. El username o email ya esta en uso'}), 409

    return jsonify({
        'id':       row['id'],
        'username': row['username'],
        'email':    row.get('email'),
        'edad':     row.get('edad'),
        'rol':      row.get('rol', 'user'),
    })
