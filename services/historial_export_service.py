"""
historial_export_service.py — Exportación segura del historial de usuario.

Genera dos formatos:
  - PDF: tabla legible con película, reacción, fecha, minutos vistos
  - XML: estructura bancaria con cada campo cifrado AES-256 + firma HMAC-SHA256

El XML puede ser descifrado por el propio usuario desde el frontend
(POST /api/usuario/historial/descifrar).
"""
import hashlib
import hmac
import json
from datetime import datetime, timezone, timedelta
from io import BytesIO
from xml.etree import ElementTree as ET

TZ_MEXICO = timezone(timedelta(hours=-6))

from core.logger import get_logger
from services.crypto_utils import get_fernet, get_hmac_secret

logger = get_logger(__name__)

# Mapeo de reacción a texto legible
_REACCION_LABEL = {
    'double_like': 'Me encantó',
    'like':        'Me gustó',
    'dislike':     'No me gustó',
}


def _cifrar(valor: str) -> str:
    """Cifra un string con AES-256-Fernet y retorna el token como string."""
    return get_fernet().encrypt(valor.encode('utf-8')).decode('utf-8')


def _descifrar(token: str) -> str:
    """Descifra un token Fernet y retorna el string original."""
    return get_fernet().decrypt(token.encode('utf-8')).decode('utf-8')


def _firmar(datos: str) -> str:
    """Genera firma HMAC-SHA256 sobre un string y la retorna en hexadecimal."""
    return hmac.new(
        get_hmac_secret(),
        datos.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def _fmt_fecha(fecha_raw) -> str:
    """Convierte una fecha ISO (UTC) a hora México (UTC-6) en formato legible."""
    if not fecha_raw:
        return '—'
    try:
        dt_utc = datetime.fromisoformat(str(fecha_raw).replace('Z', '+00:00'))
        dt_mx = dt_utc.astimezone(TZ_MEXICO)
        return dt_mx.strftime('%d/%m/%Y %H:%M')
    except Exception:
        return str(fecha_raw)[:16]


def generar_pdf_historial(historial: list, usuario: dict) -> bytes:
    """
    Genera un PDF con el historial de visualizaciones del usuario.
    Retorna los bytes del PDF.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm, leftMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )

    ROJO       = colors.HexColor('#E50914')
    OSCURO     = colors.HexColor('#0A0A0F')
    GRIS       = colors.HexColor('#6B7280')
    GRIS_CLARO = colors.HexColor('#F3F4F6')
    VERDE      = colors.HexColor('#16A34A')
    AZUL       = colors.HexColor('#1D4ED8')
    AMARILLO   = colors.HexColor('#D97706')

    estilos = getSampleStyleSheet()

    def estilo(nombre, **kw):
        return ParagraphStyle(nombre, parent=estilos['Normal'], **kw)

    s_section  = estilo('section',  fontSize=10, textColor=colors.white, fontName='Helvetica-Bold')
    s_label    = estilo('label',    fontSize=8,  textColor=GRIS,   fontName='Helvetica-Bold', spaceBefore=2)
    s_valor    = estilo('valor',    fontSize=9,  textColor=OSCURO, fontName='Helvetica')
    s_th       = estilo('th',       fontSize=8,  textColor=colors.white, fontName='Helvetica-Bold', alignment=TA_CENTER)
    s_td       = estilo('td',       fontSize=8,  textColor=OSCURO, fontName='Helvetica')
    s_td_c     = estilo('td_c',     fontSize=8,  textColor=OSCURO, fontName='Helvetica',      alignment=TA_CENTER)
    s_footer   = estilo('footer',   fontSize=7,  textColor=GRIS,   alignment=TA_CENTER)
    s_hdr_nexflis = estilo('hdr_nexflis', fontSize=26, textColor=ROJO,
                           fontName='Helvetica-Bold', alignment=TA_CENTER,
                           spaceBefore=0, spaceAfter=0, leading=30)
    s_hdr_sub  = estilo('hdr_sub', fontSize=11, textColor=OSCURO,
                        fontName='Helvetica', alignment=TA_CENTER,
                        spaceBefore=0, spaceAfter=0, leading=14)

    elementos = []

    # ── Encabezado (mismo patrón que payment_service: texto plano + HRFlowable) ──
    elementos.append(Paragraph('NEXFLIS', s_hdr_nexflis))
    elementos.append(Paragraph('Historial de Visualizaciones', s_hdr_sub))
    elementos.append(Spacer(1, 0.3 * cm))
    elementos.append(HRFlowable(width='100%', thickness=2, color=ROJO))
    elementos.append(Spacer(1, 0.4 * cm))

    # ── Datos del titular ──
    ahora_mx  = datetime.now(TZ_MEXICO)
    ahora_str = ahora_mx.strftime('%d/%m/%Y %H:%M (México)')
    tabla_meta = Table([
        [Paragraph('TITULAR',   s_label), Paragraph(usuario.get('username', ''), s_valor)],
        [Paragraph('EMAIL',     s_label), Paragraph(usuario.get('email', 'No registrado'), s_valor)],
        [Paragraph('GENERADO',  s_label), Paragraph(ahora_str, s_valor)],
        [Paragraph('REGISTROS', s_label), Paragraph(str(len(historial)), s_valor)],
    ], colWidths=[4 * cm, 13 * cm])
    tabla_meta.setStyle(TableStyle([
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, GRIS_CLARO]),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#E5E7EB')),
        ('LEFTPADDING',  (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING',   (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 4),
    ]))
    elementos.append(tabla_meta)
    elementos.append(Spacer(1, 0.5 * cm))

    # ── Tabla de historial ──
    hdr_tabla = Table([[Paragraph('  HISTORIAL DE PELÍCULAS VISTAS', s_section)]],
                      colWidths=[17 * cm])
    hdr_tabla.setStyle(TableStyle([
        ('BACKGROUND',   (0, 0), (-1, -1), OSCURO),
        ('LEFTPADDING',  (0, 0), (-1, -1), 8),
        ('TOPPADDING',   (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 6),
    ]))
    elementos.append(hdr_tabla)
    elementos.append(Spacer(1, 0.15 * cm))

    if not historial:
        elementos.append(Paragraph('Sin registros de visualización.', s_valor))
    else:
        filas = [[
            Paragraph('PELÍCULA',  s_th),
            Paragraph('REACCIÓN',  s_th),
            Paragraph('MINUTOS',   s_th),
            Paragraph('FECHA (MX)', s_th),
        ]]

        color_reaccion = {
            'double_like': VERDE,
            'like':        AZUL,
            'dislike':     AMARILLO,
        }

        for item in historial:
            titulo       = item.get('title') or item.get('titulo') or 'Sin título'
            reaccion_raw = item.get('reaccion', '')
            reaccion_label = _REACCION_LABEL.get(reaccion_raw, reaccion_raw)
            minutos      = str(item.get('minutos_vistos', 0))
            fecha_str    = _fmt_fecha(item.get('viewed_at'))

            color  = color_reaccion.get(reaccion_raw, GRIS)
            s_reac = estilo(f'reac_{reaccion_raw}_{titulo[:8]}', fontSize=8, textColor=color,
                            fontName='Helvetica-Bold', alignment=TA_CENTER)
            filas.append([
                Paragraph(titulo[:50], s_td),
                Paragraph(reaccion_label, s_reac),
                Paragraph(minutos, s_td_c),
                Paragraph(fecha_str, s_td_c),
            ])

        tabla_hist = Table(filas, colWidths=[7.5 * cm, 3.5 * cm, 2.5 * cm, 3.5 * cm])
        tabla_hist.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0), OSCURO),
            ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, GRIS_CLARO]),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#E5E7EB')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING',  (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING',   (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING',(0, 0), (-1, -1), 4),
        ]))
        elementos.append(tabla_hist)

    elementos.append(Spacer(1, 0.6 * cm))
    elementos.append(HRFlowable(width='100%', thickness=0.5, color=GRIS))
    elementos.append(Spacer(1, 0.2 * cm))
    elementos.append(Paragraph(
        f'Generado el {ahora_str} · NEXFLIS · Documento confidencial',
        s_footer,
    ))

    doc.build(elementos)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# XML cifrado
# ---------------------------------------------------------------------------

def generar_xml_historial(historial: list, usuario: dict) -> str:
    """
    Genera el XML del historial con cada campo sensible cifrado AES-256-Fernet.
    La firma HMAC-SHA256 se calcula sobre el contenido serializado antes de cifrar
    para garantizar integridad del documento completo.
    """
    ahora_iso = datetime.now(TZ_MEXICO).isoformat()

    # Construir representación canónica para firmar (antes de cifrar)
    registros_raw = []
    for i, item in enumerate(historial, 1):
        titulo = item.get('title') or item.get('titulo') or 'Sin título'
        reaccion_raw = item.get('reaccion', '')
        reaccion_label = _REACCION_LABEL.get(reaccion_raw, reaccion_raw)
        minutos = str(item.get('minutos_vistos', 0))
        fecha_str = _fmt_fecha(item.get('viewed_at'))
        registros_raw.append({
            'id':      i,
            'pelicula': titulo,
            'reaccion': reaccion_label,
            'fecha':    fecha_str,
            'minutos':  minutos,
        })

    # Datos canónicos para firma (incluye titular + todos los registros)
    datos_para_firma = json.dumps({
        'titular':    usuario.get('username', ''),
        'generado':   ahora_iso,
        'registros':  registros_raw,
    }, ensure_ascii=False, sort_keys=True)

    firma_hex = _firmar(datos_para_firma)

    # Construir XML
    raiz = ET.Element('historial', {
        'version':  '1.0',
        'generado': ahora_iso,
        'firma':    firma_hex,
    })

    ET.SubElement(raiz, 'emisor').text = 'NEXFLIS'

    titular_el = ET.SubElement(raiz, 'titular')
    titular_el.set('cifrado', 'AES256')
    titular_el.text = _cifrar(usuario.get('username', ''))

    registros_el = ET.SubElement(raiz, 'registros', {'total': str(len(historial))})

    for reg in registros_raw:
        reg_el = ET.SubElement(registros_el, 'registro', {'id': str(reg['id'])})

        pelicula_el = ET.SubElement(reg_el, 'pelicula')
        pelicula_el.set('cifrado', 'AES256')
        pelicula_el.text = _cifrar(reg['pelicula'])

        reaccion_el = ET.SubElement(reg_el, 'reaccion')
        reaccion_el.set('cifrado', 'AES256')
        reaccion_el.text = _cifrar(reg['reaccion'])

        fecha_el = ET.SubElement(reg_el, 'fecha')
        fecha_el.set('cifrado', 'AES256')
        fecha_el.text = _cifrar(reg['fecha'])

        minutos_el = ET.SubElement(reg_el, 'minutos')
        minutos_el.set('cifrado', 'AES256')
        minutos_el.text = _cifrar(reg['minutos'])

    # Serializar con declaración XML + DTD
    tree_str = ET.tostring(raiz, encoding='unicode', xml_declaration=False)
    dtd = '<!DOCTYPE historial SYSTEM "nexflis-historial.dtd">'
    xml_completo = f'<?xml version="1.0" encoding="UTF-8"?>\n{dtd}\n{tree_str}'
    return xml_completo


# ---------------------------------------------------------------------------
# Descifrador de XML
# ---------------------------------------------------------------------------

def descifrar_xml_historial(xml_str: str) -> dict:
    """
    Descifra un XML de historial generado por generar_xml_historial().

    Retorna:
        {
            'valido': bool,
            'firma_ok': bool,
            'titular': str,
            'generado': str,
            'registros': [{'pelicula', 'reaccion', 'fecha', 'minutos'}, ...]
        }
    """
    try:
        # Eliminar DTD si está presente (ET no soporta DOCTYPE externo)
        lineas = [l for l in xml_str.splitlines()
                  if not l.strip().startswith('<!DOCTYPE')]
        xml_limpio = '\n'.join(lineas)

        raiz = ET.fromstring(xml_limpio)
    except ET.ParseError as exc:
        logger.error('descifrar_xml_historial: XML malformado — %s', exc)
        return {'valido': False, 'firma_ok': False, 'titular': '', 'generado': '', 'registros': []}

    firma_guardada = raiz.get('firma', '')
    generado       = raiz.get('generado', '')

    # Descifrar titular
    try:
        titular = _descifrar(raiz.findtext('titular') or '')
    except Exception:
        logger.error('descifrar_xml_historial: error al descifrar titular', exc_info=True)
        return {'valido': False, 'firma_ok': False, 'titular': '', 'generado': generado, 'registros': []}

    # Descifrar registros
    registros = []
    for reg_el in raiz.findall('.//registro'):
        try:
            pelicula = _descifrar(reg_el.findtext('pelicula') or '')
            reaccion = _descifrar(reg_el.findtext('reaccion') or '')
            fecha    = _descifrar(reg_el.findtext('fecha')    or '')
            minutos  = _descifrar(reg_el.findtext('minutos')  or '')
            registros.append({
                'pelicula': pelicula,
                'reaccion': reaccion,
                'fecha':    fecha,
                'minutos':  minutos,
            })
        except Exception:
            logger.error('descifrar_xml_historial: error al descifrar registro id=%s',
                         reg_el.get('id', '?'), exc_info=True)
            return {'valido': False, 'firma_ok': False, 'titular': titular,
                    'generado': generado, 'registros': []}

    # Recalcular firma para verificar integridad
    datos_para_firma = json.dumps({
        'titular':   titular,
        'generado':  generado,
        'registros': [
            {'id': i + 1, 'pelicula': r['pelicula'], 'reaccion': r['reaccion'],
             'fecha': r['fecha'], 'minutos': r['minutos']}
            for i, r in enumerate(registros)
        ],
    }, ensure_ascii=False, sort_keys=True)

    firma_calculada = _firmar(datos_para_firma)
    firma_ok = hmac.compare_digest(firma_calculada, firma_guardada)

    return {
        'valido':    True,
        'firma_ok':  firma_ok,
        'titular':   titular,
        'generado':  generado,
        'registros': registros,
    }
