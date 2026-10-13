"""
historial_routes.py — Exportación del historial de usuario.

Endpoints:
  GET  /api/usuario/historial/pdf      → descarga PDF del historial
  GET  /api/usuario/historial/xml      → descarga XML cifrado del historial
  POST /api/usuario/historial/descifrar → descifra XML y retorna registros en JSON
"""
from flask import Blueprint, jsonify, request, Response

from core.logger import get_logger
from routes.jwt_middleware import jwt_required
from services.historial_export_service import (
    generar_pdf_historial,
    generar_xml_historial,
    descifrar_xml_historial,
)

logger = get_logger(__name__)

bp = Blueprint('historial_export', __name__)

_db = None


def register(app, db_service, csrf=None):
    global _db
    _db = db_service
    if csrf:
        csrf.exempt(api_historial_pdf)
        csrf.exempt(api_historial_xml)
        csrf.exempt(api_historial_descifrar)
    app.register_blueprint(bp)


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

@bp.route('/api/usuario/historial/pdf', methods=['GET'])
@jwt_required
def api_historial_pdf(usuario):
    if not _db:
        return jsonify({'error': 'BD no disponible'}), 503

    historial = _db.obtener_historial_usuario(usuario.id, limit=100)
    usuario_dict = {
        'username': usuario.username,
        'email':    getattr(usuario, 'email', '') or '',
    }

    try:
        pdf_bytes = generar_pdf_historial(historial, usuario_dict)
    except Exception:
        logger.error('Error generando PDF historial para usuario_id=%s', usuario.id, exc_info=True)
        return jsonify({'error': 'No se pudo generar el PDF'}), 500

    return Response(
        pdf_bytes,
        status=200,
        mimetype='application/pdf',
        headers={
            'Content-Disposition': f'attachment; filename="historial_{usuario.username}.pdf"',
            'Content-Length': str(len(pdf_bytes)),
        },
    )


# ---------------------------------------------------------------------------
# XML cifrado
# ---------------------------------------------------------------------------

@bp.route('/api/usuario/historial/xml', methods=['GET'])
@jwt_required
def api_historial_xml(usuario):
    if not _db:
        return jsonify({'error': 'BD no disponible'}), 503

    historial = _db.obtener_historial_usuario(usuario.id, limit=100)
    usuario_dict = {
        'username': usuario.username,
        'email':    getattr(usuario, 'email', '') or '',
    }

    try:
        xml_str = generar_xml_historial(historial, usuario_dict)
    except Exception:
        logger.error('Error generando XML historial para usuario_id=%s', usuario.id, exc_info=True)
        return jsonify({'error': 'No se pudo generar el XML'}), 500

    xml_bytes = xml_str.encode('utf-8')
    return Response(
        xml_bytes,
        status=200,
        mimetype='application/xml',
        headers={
            'Content-Disposition': f'attachment; filename="historial_{usuario.username}.xml"',
            'Content-Length': str(len(xml_bytes)),
        },
    )


# ---------------------------------------------------------------------------
# Descifrador
# ---------------------------------------------------------------------------

@bp.route('/api/usuario/historial/descifrar', methods=['POST'])
@jwt_required
def api_historial_descifrar(usuario):
    """
    Recibe el XML cifrado pegado desde el frontend y retorna los registros descifrados.
    Solo el usuario autenticado puede descifrar su propio historial
    (misma clave AES derivada del servidor; el usuario no puede generarla por sí solo).
    """
    datos = request.get_json(silent=True) or {}
    xml_str = datos.get('xml', '').strip()

    if not xml_str:
        return jsonify({'error': 'XML vacío o no enviado'}), 400

    try:
        resultado = descifrar_xml_historial(xml_str)
    except Exception:
        logger.error('Error en descifrado XML historial usuario_id=%s', usuario.id, exc_info=True)
        return jsonify({'error': 'Error interno al descifrar'}), 500

    if not resultado['valido']:
        return jsonify({'error': 'XML inválido o con datos corruptos'}), 422

    return jsonify(resultado), 200
