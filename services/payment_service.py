"""
payment_service.py — Simulación educativa de pagos seguros.

Implementa los mismos patrones de seguridad que la banca electrónica:
  - AES-256 (Fernet) para cifrar datos sensibles de la transacción
  - HMAC-SHA256 para firma digital (garantiza integridad)
  - PDF con datos legibles + sección cifrada + instrucciones de verificación
"""
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone
from io import BytesIO

from core.logger import get_logger
from services.crypto_utils import get_fernet as _get_fernet, get_hmac_secret as _get_hmac_secret

logger = get_logger(__name__)


class PaymentService:

    MONTO = 99.99
    MONEDA = 'MXN'
    PLAN_DURACION_DIAS = 30

    # ------------------------------------------------------------------
    # Generar transacción
    # ------------------------------------------------------------------

    def generar_transaccion(self, usuario: dict, numero_tarjeta: str) -> dict:
        """
        Genera una transacción simulada con seguridad bancaria:
          1. Crea ID único de transacción
          2. Cifra datos sensibles con AES-256 (Fernet)
          3. Genera firma HMAC-SHA256 para integridad
          4. Retorna todo listo para guardar en BD y generar PDF
        """
        txn_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
        ahora = datetime.now(timezone.utc)
        expires_at = ahora + timedelta(days=self.PLAN_DURACION_DIAS)
        ultimos_digitos = numero_tarjeta.replace(' ', '')[-4:]

        # Payload con datos sensibles que van CIFRADOS
        payload_sensible = {
            'txn_id':          txn_id,
            'usuario_id':      usuario['id'],
            'username':        usuario['username'],
            'email':           usuario.get('email', ''),
            'plan':            'premium',
            'monto':           self.MONTO,
            'moneda':          self.MONEDA,
            'ultimos_digitos': ultimos_digitos,
            'timestamp':       ahora.isoformat(),
            'expires_at':      expires_at.isoformat(),
            'ip_simulada':     '192.168.1.x',
        }

        # 1. Cifrar con AES-256
        fernet = _get_fernet()
        payload_json = json.dumps(payload_sensible, ensure_ascii=False)
        payload_cifrado = fernet.encrypt(payload_json.encode()).decode()

        # 2. Firma HMAC-SHA256 sobre el payload cifrado
        firma = hmac.new(
            _get_hmac_secret(),
            payload_cifrado.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return {
            'txn_id':          txn_id,
            'usuario_id':      usuario['id'],
            'ultimos_digitos': ultimos_digitos,
            'payload_cifrado': payload_cifrado,
            'hmac_firma':      firma,
            'expires_at':      expires_at,
            'payload_legible': payload_sensible,
        }

    # ------------------------------------------------------------------
    # Descifrar transacción (para el endpoint de verificación)
    # ------------------------------------------------------------------

    def descifrar_transaccion(self, txn_row: dict) -> dict:
        """
        Descifra los datos de una transacción y verifica la firma HMAC.
        Retorna: {'valida': bool, 'datos': dict, 'firma_ok': bool}
        """
        payload_cifrado = txn_row['payload_cifrado']
        firma_guardada  = txn_row['hmac_firma']

        # 1. Verificar integridad con HMAC antes de descifrar
        firma_calculada = hmac.new(
            _get_hmac_secret(),
            payload_cifrado.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        firma_ok = hmac.compare_digest(firma_calculada, firma_guardada)

        # 2. Descifrar con AES-256
        try:
            fernet = _get_fernet()
            datos_json = fernet.decrypt(payload_cifrado.encode()).decode()
            datos = json.loads(datos_json)
        except Exception:
            logger.error('Error al descifrar transacción', exc_info=True)
            return {'valida': False, 'datos': {}, 'firma_ok': False}

        return {'valida': True, 'datos': datos, 'firma_ok': firma_ok}

    # ------------------------------------------------------------------
    # Generar PDF del comprobante
    # ------------------------------------------------------------------

    def generar_pdf(self, txn_row: dict, usuario: dict) -> bytes:
        """
        Genera un PDF profesional estilo comprobante bancario con:
          - Datos legibles de la transacción
          - Sección de datos cifrados (AES-256)
          - Firma HMAC para verificación de integridad
          - Instrucciones para verificar en el sistema
        """
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm, leftMargin=2*cm,
            topMargin=2*cm, bottomMargin=2*cm,
        )

        # Colores
        ROJO      = colors.HexColor('#E50914')
        OSCURO    = colors.HexColor('#0A0A0F')
        GRIS      = colors.HexColor('#6B7280')
        GRIS_CLARO= colors.HexColor('#F3F4F6')
        VERDE     = colors.HexColor('#16A34A')
        AZUL      = colors.HexColor('#1D4ED8')

        estilos = getSampleStyleSheet()

        def estilo(nombre, **kw):
            return ParagraphStyle(nombre, parent=estilos['Normal'], **kw)

        s_label     = estilo('label',     fontSize=8,  textColor=GRIS,   fontName='Helvetica-Bold', spaceBefore=2)
        s_valor     = estilo('valor',     fontSize=10, textColor=OSCURO, fontName='Helvetica')
        s_section   = estilo('section',   fontSize=10, textColor=colors.white, fontName='Helvetica-Bold', alignment=TA_LEFT)
        s_mono_azul = estilo('mono_azul', fontSize=7,  textColor=AZUL,   fontName='Courier', leading=10)
        s_footer    = estilo('footer',    fontSize=7,  textColor=GRIS,   alignment=TA_CENTER)
        s_valido    = estilo('valido',    fontSize=10, textColor=VERDE,  fontName='Helvetica-Bold', alignment=TA_CENTER)

        expires_at  = txn_row.get('expires_at') or txn_row.get('expires_at')
        created_at  = txn_row.get('created_at')
        if hasattr(expires_at, 'strftime'):
            expires_str = expires_at.strftime('%d/%m/%Y %H:%M UTC')
        else:
            expires_str = str(expires_at)[:16]
        if hasattr(created_at, 'strftime'):
            fecha_str = created_at.strftime('%d/%m/%Y %H:%M:%S UTC')
        else:
            fecha_str = str(created_at)[:19] if created_at else datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S UTC')

        elementos = []

        # ── Encabezado: un solo bloque para evitar superposición ──
        s_hdr_nexflis = estilo('hdr_nexflis', fontSize=26, textColor=ROJO,
                               fontName='Helvetica-Bold', alignment=TA_CENTER,
                               spaceBefore=0, spaceAfter=0, leading=30)
        s_hdr_sub     = estilo('hdr_sub', fontSize=11, textColor=OSCURO,
                               fontName='Helvetica', alignment=TA_CENTER,
                               spaceBefore=0, spaceAfter=0, leading=14)
        elementos.append(Paragraph('NEXFLIS', s_hdr_nexflis))
        elementos.append(Paragraph('Comprobante de Transacción', s_hdr_sub))
        elementos.append(Spacer(1, 0.3*cm))
        elementos.append(HRFlowable(width='100%', thickness=2, color=ROJO))
        elementos.append(Spacer(1, 0.35*cm))

        # Badge APROBADO
        elementos.append(Paragraph('✓  PAGO APROBADO', s_valido))
        elementos.append(Spacer(1, 0.35*cm))

        # ── Datos de la transacción ──
        def fila(label, valor):
            return [Paragraph(label, s_label), Paragraph(str(valor), s_valor)]

        tabla_datos = Table([
            fila('ID DE TRANSACCIÓN',       txn_row['txn_id']),
            fila('FECHA Y HORA',            fecha_str),
            fila('TITULAR',                 usuario.get('username', '')),
            fila('CORREO',                  usuario.get('email', 'No registrado')),
            fila('PLAN ADQUIRIDO',          'NEXFLIS Premium'),
            fila('MONTO',                   f"${self.MONTO:.2f} {self.MONEDA} (simulado)"),
            fila('TARJETA',                 f"**** **** **** {txn_row['ultimos_digitos']}"),
            fila('VIGENCIA DEL PLAN',       f"Hasta {expires_str}"),
        ], colWidths=[5*cm, 12*cm])

        tabla_datos.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.white),
            ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.white, GRIS_CLARO]),
            ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#E5E7EB')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING',  (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING',   (0,0), (-1,-1), 5),
            ('BOTTOMPADDING',(0,0), (-1,-1), 5),
        ]))
        elementos.append(tabla_datos)
        elementos.append(Spacer(1, 0.6*cm))

        # ── Sección seguridad ──
        hdr_seg = Table([[Paragraph('  🔐  DATOS CIFRADOS DE LA TRANSACCIÓN  (AES-256 + HMAC-SHA256)', s_section)]],
                        colWidths=[17*cm])
        hdr_seg.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), OSCURO),
            ('LEFTPADDING',  (0,0), (-1,-1), 8),
            ('TOPPADDING',   (0,0), (-1,-1), 6),
            ('BOTTOMPADDING',(0,0), (-1,-1), 6),
            ('ROUNDEDCORNERS', [4]),
        ]))
        elementos.append(hdr_seg)
        elementos.append(Spacer(1, 0.2*cm))

        nota_cifrado = (
            '<b>¿Qué es esto?</b> Los datos sensibles de esta transacción están cifrados con AES-256, '
            'el mismo estándar que usan los bancos y sistemas de pago (PCI-DSS). '
            'Solo el servidor NEXFLIS puede descifrarlos. '
            'La firma HMAC-SHA256 garantiza que nadie modificó este comprobante después de emitirse.'
        )
        elementos.append(Paragraph(nota_cifrado, estilo('nota', fontSize=8, textColor=GRIS, leading=12)))
        elementos.append(Spacer(1, 0.3*cm))

        # Payload cifrado partido en líneas de 72 chars con guión de continuación visible
        # Se usa &shy; (soft hyphen = nada) para evitar que ReportLab inserte guiones tipográficos
        cifrado = txn_row['payload_cifrado']
        lineas_cifrado = [cifrado[i:i+72] for i in range(0, len(cifrado), 72)]
        elementos.append(Paragraph('<b>PAYLOAD CIFRADO (AES-256-Fernet):</b>', s_label))
        s_mono_raw = estilo('mono_raw', fontSize=7, textColor=OSCURO, fontName='Courier',
                            leading=10, wordWrap='CJK')
        for linea in lineas_cifrado:
            elementos.append(Paragraph(linea, s_mono_raw))
        elementos.append(Spacer(1, 0.3*cm))

        # Firma HMAC
        elementos.append(Paragraph('<b>FIRMA DIGITAL (HMAC-SHA256):</b>', s_label))
        elementos.append(Paragraph(txn_row['hmac_firma'], s_mono_azul))
        elementos.append(Spacer(1, 0.4*cm))

        # ── Instrucciones de verificación ──
        hdr_ver = Table([[Paragraph('  🔍  VERIFICAR INTEGRIDAD DE ESTE COMPROBANTE', s_section)]],
                        colWidths=[17*cm])
        hdr_ver.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), AZUL),
            ('LEFTPADDING',  (0,0), (-1,-1), 8),
            ('TOPPADDING',   (0,0), (-1,-1), 6),
            ('BOTTOMPADDING',(0,0), (-1,-1), 6),
        ]))
        elementos.append(hdr_ver)
        elementos.append(Spacer(1, 0.2*cm))

        instrucciones = (
            f'Para verificar que este comprobante es auténtico y no ha sido alterado, '
            f'ingresa el <b>ID de transacción</b> en la sección "Verificar comprobante" de tu perfil '
            f'o accede directamente a:<br/>'
            f'<font color="#1D4ED8"><b>/api/transacciones/{txn_row["txn_id"]}/verificar</b></font><br/><br/>'
            f'El sistema descifra el payload, recalcula la firma HMAC y confirma si los datos son idénticos '
            f'a los registrados al momento del pago. Si alguien modificó este PDF, la firma no coincidirá.'
        )
        elementos.append(Paragraph(instrucciones, estilo('instr', fontSize=8, textColor=OSCURO, leading=13)))
        elementos.append(Spacer(1, 0.6*cm))

        elementos.append(HRFlowable(width='100%', thickness=0.5, color=GRIS))
        elementos.append(Spacer(1, 0.2*cm))
        elementos.append(Paragraph(
            f'Generado el {datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")} · '
            f'AES-256-Fernet · HMAC-SHA256 · NEXFLIS',
            s_footer
        ))

        doc.build(elementos)
        return buffer.getvalue()
