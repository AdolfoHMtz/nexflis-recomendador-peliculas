"""
payment_routes.py — Endpoints de pago y verificación de comprobantes.

  POST /api/suscripcion/pagar          → Procesa pago simulado, genera transacción
  GET  /api/suscripcion/plan           → Retorna plan actual del usuario
  GET  /api/transacciones/{txn_id}/pdf → Descarga PDF del comprobante
  GET  /api/transacciones/{txn_id}/verificar → Descifra y verifica integridad
"""
from flask import Blueprint, jsonify, request, send_file
from io import BytesIO

from routes.jwt_middleware import jwt_required
from services.payment_service import PaymentService

bp = Blueprint('payment', __name__)
_db = None
_payment: PaymentService = None


def register(app, db_service, csrf=None):
    global _db, _payment
    _db = db_service
    _payment = PaymentService()
    if csrf:
        csrf.exempt(bp)
    app.register_blueprint(bp)


# ---------------------------------------------------------------------------
# POST /api/suscripcion/pagar
# ---------------------------------------------------------------------------

@bp.route('/api/suscripcion/pagar', methods=['POST'])
@jwt_required
def pagar(usuario):
    """Simula un pago Premium. Genera transacción cifrada y actualiza el plan."""
    data = request.get_json(silent=True) or {}
    numero_tarjeta = str(data.get('numero_tarjeta', '')).replace(' ', '')

    if len(numero_tarjeta) < 13 or len(numero_tarjeta) > 19:
        return jsonify({'error': 'Número de tarjeta inválido'}), 400
    if not numero_tarjeta.isdigit():
        return jsonify({'error': 'La tarjeta solo debe contener dígitos'}), 400

    # Verificar que no tenga ya un plan premium activo
    plan_actual = _db.get_plan_usuario(usuario.id)
    if plan_actual['plan'] == 'premium':
        return jsonify({'error': 'Ya tienes un plan Premium activo'}), 409

    usuario_dict = {
        'id':       usuario.id,
        'username': usuario.username,
        'email':    getattr(usuario, 'email', None),
    }
    if not usuario_dict['email']:
        fila = _db.get_user_by_id(usuario.id)
        if fila:
            usuario_dict['email'] = fila.get('email', '')

    # Generar transacción con cifrado
    txn = _payment.generar_transaccion(usuario_dict, numero_tarjeta)

    # Guardar en BD
    row = _db.crear_transaccion(
        txn_id          = txn['txn_id'],
        usuario_id      = txn['usuario_id'],
        ultimos_digitos = txn['ultimos_digitos'],
        payload_cifrado = txn['payload_cifrado'],
        hmac_firma      = txn['hmac_firma'],
        expires_at      = txn['expires_at'],
    )
    if not row:
        return jsonify({'error': 'Error al procesar el pago'}), 500

    return jsonify({
        'txn_id':      txn['txn_id'],
        'plan':        'premium',
        'expires_at':  txn['expires_at'].isoformat(),
        'mensaje':     '¡Bienvenido a NEXFLIS Premium!',
    }), 201


# ---------------------------------------------------------------------------
# GET /api/suscripcion/plan
# ---------------------------------------------------------------------------

@bp.route('/api/suscripcion/plan', methods=['GET'])
@jwt_required
def get_plan(usuario):
    """Retorna el plan actual del usuario con fecha de expiración."""
    plan_info = _db.get_plan_usuario(usuario.id)
    return jsonify(plan_info)


# ---------------------------------------------------------------------------
# GET /api/transacciones/<txn_id>/pdf
# ---------------------------------------------------------------------------

@bp.route('/api/transacciones/<txn_id>/pdf', methods=['GET'])
@jwt_required
def descargar_pdf(usuario, txn_id):
    """Genera y descarga el PDF del comprobante de transacción."""
    txn_row = _db.get_transaccion(txn_id)
    if not txn_row:
        return jsonify({'error': 'Transacción no encontrada'}), 404
    if txn_row['usuario_id'] != usuario.id:
        return jsonify({'error': 'No autorizado'}), 403

    usuario_dict = {
        'id':       usuario.id,
        'username': usuario.username,
        'email':    getattr(usuario, 'email', None),
    }
    if not usuario_dict['email']:
        fila = _db.get_user_by_id(usuario.id)
        if fila:
            usuario_dict['email'] = fila.get('email', '')

    pdf_bytes = _payment.generar_pdf(txn_row, usuario_dict)

    return send_file(
        BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'comprobante_{txn_id}.pdf',
    )


# ---------------------------------------------------------------------------
# GET /api/transacciones/<txn_id>/pdf  — también acepta la última del usuario
# ---------------------------------------------------------------------------

@bp.route('/api/suscripcion/ultimo-comprobante/pdf', methods=['GET'])
@jwt_required
def descargar_ultimo_pdf(usuario):
    """Descarga el PDF de la transacción más reciente del usuario."""
    txn_row = _db.get_ultima_transaccion_usuario(usuario.id)
    if not txn_row:
        return jsonify({'error': 'No tienes transacciones registradas'}), 404

    usuario_dict = {'id': usuario.id, 'username': usuario.username, 'email': getattr(usuario, 'email', None)}
    if not usuario_dict['email']:
        fila = _db.get_user_by_id(usuario.id)
        if fila:
            usuario_dict['email'] = fila.get('email', '')

    pdf_bytes = _payment.generar_pdf(txn_row, usuario_dict)
    return send_file(
        BytesIO(pdf_bytes), mimetype='application/pdf',
        as_attachment=True, download_name=f'comprobante_{txn_row["txn_id"]}.pdf',
    )


# ---------------------------------------------------------------------------
# GET /api/transacciones/<txn_id>/verificar  — por ID desde BD
# ---------------------------------------------------------------------------

@bp.route('/api/transacciones/<txn_id>/verificar', methods=['GET'])
@jwt_required
def verificar_transaccion(usuario, txn_id):
    """Descifra y verifica integridad de una transacción por su ID."""
    txn_row = _db.get_transaccion(txn_id)
    if not txn_row:
        return jsonify({'error': 'Transacción no encontrada'}), 404
    if txn_row['usuario_id'] != usuario.id:
        return jsonify({'error': 'No autorizado'}), 403

    resultado = _payment.descifrar_transaccion(txn_row)
    return jsonify({
        'txn_id':   txn_id,
        'firma_ok': resultado['firma_ok'],
        'integro':  resultado['valida'] and resultado['firma_ok'],
        'datos':    resultado['datos'],
        'mensaje':  (
            '✓ Comprobante íntegro. La firma HMAC coincide, los datos no han sido alterados.'
            if resultado['firma_ok']
            else '✗ ADVERTENCIA: La firma no coincide. Este comprobante puede haber sido modificado.'
        ),
    })


# ---------------------------------------------------------------------------
# POST /api/transacciones/verificar-payload — descifra payload pegado a mano
# ---------------------------------------------------------------------------

@bp.route('/api/transacciones/verificar-payload', methods=['POST'])
@jwt_required
def verificar_payload(usuario):
    """
    Descifra un payload AES-256 pegado directamente (del PDF).
    No requiere txn_id — funciona solo con el texto cifrado + firma HMAC del comprobante.
    Body: { "payload_cifrado": "gAAAAA...", "hmac_firma": "3f2c..." }
    """
    data = request.get_json(silent=True) or {}
    # Limpiar solo whitespace — NO tocar el contenido base64 (_, -, =, letras, dígitos)
    import re as _re
    payload_cifrado = _re.sub(r'\s+', '', str(data.get('payload_cifrado', '')))
    hmac_firma      = str(data.get('hmac_firma', '')).strip()

    if not payload_cifrado:
        return jsonify({'error': 'Falta el payload cifrado'}), 400
    if not hmac_firma:
        return jsonify({'error': 'Falta la firma HMAC'}), 400

    resultado = _payment.descifrar_transaccion({
        'payload_cifrado': payload_cifrado,
        'hmac_firma':      hmac_firma,
    })

    if not resultado['valida']:
        return jsonify({
            'firma_ok': False, 'integro': False, 'datos': {},
            'mensaje': '✗ Payload inválido o corrupto. No se pudo descifrar.',
        }), 400

    # Seguridad: solo mostrar si el payload pertenece al usuario autenticado
    datos = resultado['datos']
    if str(datos.get('usuario_id')) != str(usuario.id):
        return jsonify({'error': 'Este comprobante no pertenece a tu cuenta'}), 403

    return jsonify({
        'firma_ok': resultado['firma_ok'],
        'integro':  resultado['valida'] and resultado['firma_ok'],
        'datos':    datos,  # siempre se muestran aunque la firma falle
        'mensaje':  (
            '✓ Comprobante auténtico. Firma HMAC válida, datos íntegros.'
            if resultado['firma_ok']
            else '✗ ADVERTENCIA: La firma HMAC no coincide. Los datos se muestran pero el comprobante puede haber sido alterado.'
        ),
    })
