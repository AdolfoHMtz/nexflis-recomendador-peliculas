import { useState } from 'react'
import Dialog from '@mui/material/Dialog'
import DialogContent from '@mui/material/DialogContent'
import IconButton from '@mui/material/IconButton'
import CloseIcon from '@mui/icons-material/Close'
import { verificarPayload } from '../../api/payment'

const CAMPO_LABELS = {
  txn_id:          'ID de transacción',
  usuario_id:      'ID de usuario',
  username:        'Titular',
  email:           'Correo',
  plan:            'Plan',
  monto:           'Monto',
  moneda:          'Moneda',
  ultimos_digitos: 'Tarjeta',
  timestamp:       'Fecha de pago',
  expires_at:      'Vigencia hasta',
}

export default function VerifyModal({ open, onClose }) {
  const [payloadCifrado, setPayloadCifrado] = useState('')
  const [hmacFirma, setHmacFirma]           = useState('')
  const [resultado, setResultado]           = useState(null)
  const [loading, setLoading]               = useState(false)
  const [error, setError]                   = useState('')

  const handleClose = () => {
    setPayloadCifrado(''); setHmacFirma(''); setResultado(null); setError('')
    onClose()
  }

  const handleVerificar = async (e) => {
    e.preventDefault()
    setError(''); setResultado(null)
    const payloadLimpio = payloadCifrado.replace(/\s+/g, '')
    if (!payloadLimpio) { setError('Pega el payload cifrado del PDF'); return }
    if (!hmacFirma.trim()) { setError('Pega la firma HMAC del PDF'); return }
    setLoading(true)
    try {
      const res = await verificarPayload(payloadLimpio, hmacFirma.trim())
      setResultado(res)
    } catch (err) {
      const msg = err?.response?.data?.error || 'Error al verificar'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const taStyle = {
    width: '100%', background: '#0a0a15', border: '1px solid #2a2a4a',
    color: '#e5e5e5', borderRadius: 10, padding: '10px 13px',
    fontSize: '.75rem', fontFamily: 'monospace', outline: 'none',
    boxSizing: 'border-box', resize: 'vertical', lineHeight: 1.5,
    transition: 'border-color .2s',
  }

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          background: '#12121f', border: '1px solid #1e1e3a',
          borderRadius: '20px', color: '#e5e5e5',
          boxShadow: '0 25px 60px rgba(0,0,0,.8)',
        },
      }}
    >
      <DialogContent sx={{ p: 0 }}>

        {/* Header */}
        <div style={{ padding: '20px 22px 16px', borderBottom: '1px solid #1a1a2e', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: '1rem', color: '#f0f0f0' }}>Verificar comprobante</div>
            <div style={{ fontSize: '.75rem', color: '#6b7280', marginTop: 3, lineHeight: 1.5 }}>
              Pega el payload cifrado y la firma de tu PDF para descifrar y verificar la autenticidad del pago
            </div>
          </div>
          <IconButton onClick={handleClose} size="small" sx={{ color: '#6b7280', mt: '-4px', '&:hover': { color: '#e5e5e5' } }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </div>

        <div style={{ padding: '18px 22px 22px' }}>

          {/* Explicación educativa */}
          <div style={{ background: 'rgba(29,78,216,.07)', border: '1px solid rgba(29,78,216,.25)', borderRadius: 10, padding: '12px 14px', marginBottom: 18 }}>
            <div style={{ fontSize: '.78rem', color: '#93c5fd', lineHeight: 1.7 }}>
              <strong style={{ color: '#bfdbfe' }}>¿Cómo funciona?</strong><br />
              Tu comprobante PDF contiene dos bloques de texto: el <strong>Payload cifrado</strong> (AES-256) y la <strong>Firma HMAC-SHA256</strong>.
              Al pegar ambos aquí, el servidor:
              <ol style={{ margin: '6px 0 0 16px', padding: 0 }}>
                <li>Recalcula la firma HMAC con la clave secreta de la app</li>
                <li>La compara con la firma del PDF — si no coincide, el PDF fue alterado</li>
                <li>Descifra el payload con AES-256 y muestra los datos originales del pago</li>
              </ol>
              <br />
              <strong style={{ color: '#bfdbfe' }}>Clave secreta (llave AES):</strong> Nunca sale del servidor. Sin ella, el payload cifrado es ilegible — exactamente como en banca electrónica (estándar PCI-DSS).
            </div>
          </div>

          <form onSubmit={handleVerificar}>
            <div style={{ marginBottom: 14 }}>
              <label style={{ fontSize: '.72rem', color: '#6b7280', display: 'block', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '.04em' }}>
                Payload cifrado (AES-256-Fernet) — del PDF
              </label>
              <textarea
                rows={5}
                value={payloadCifrado}
                onChange={e => setPayloadCifrado(e.target.value)}
                placeholder="gAAAAABp6F..."
                style={taStyle}
                onFocus={e => e.target.style.borderColor = '#1d4ed8'}
                onBlur={e => e.target.style.borderColor = '#2a2a4a'}
              />
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: '.72rem', color: '#6b7280', display: 'block', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '.04em' }}>
                Firma digital (HMAC-SHA256) — del PDF
              </label>
              <input
                type="text"
                value={hmacFirma}
                onChange={e => setHmacFirma(e.target.value)}
                placeholder="12529e41f3b5e00e..."
                style={{ ...taStyle, resize: 'none', fontFamily: 'monospace', padding: '10px 13px' }}
                onFocus={e => e.target.style.borderColor = '#1d4ed8'}
                onBlur={e => e.target.style.borderColor = '#2a2a4a'}
              />
            </div>

            {error && (
              <div style={{ background: 'rgba(229,9,20,.08)', border: '1px solid rgba(229,9,20,.3)', color: '#f87171', padding: '8px 12px', borderRadius: 10, fontSize: '.82rem', marginBottom: 14 }}>
                ⚠ {error}
              </div>
            )}

            <button
              type="submit" disabled={loading}
              style={{
                width: '100%', padding: '11px',
                background: loading ? '#1f1f35' : 'linear-gradient(135deg,#1d4ed8,#1e3a8a)',
                color: loading ? '#6b7280' : '#fff', border: 'none', borderRadius: 30,
                fontWeight: 700, fontSize: '.9rem', cursor: loading ? 'not-allowed' : 'pointer',
              }}
            >
              {loading ? 'Descifrando...' : 'Descifrar y verificar'}
            </button>
          </form>

          {/* Resultado */}
          {resultado && (
            <div style={{ marginTop: 20 }}>
              <div style={{ borderTop: '1px solid #1a1a2e', marginBottom: 16 }} />

              {/* Badge resultado firma */}
              <div style={{
                padding: '12px 14px', borderRadius: 10, marginBottom: 12,
                background: resultado.firma_ok ? 'rgba(34,197,94,.08)' : 'rgba(234,179,8,.08)',
                border: `1px solid ${resultado.firma_ok ? 'rgba(34,197,94,.3)' : 'rgba(234,179,8,.35)'}`,
              }}>
                <div style={{ fontWeight: 700, fontSize: '.88rem', color: resultado.firma_ok ? '#4ade80' : '#fbbf24', marginBottom: 6 }}>
                  {resultado.firma_ok ? '✓ Firma HMAC válida — comprobante íntegro' : '⚠ Firma HMAC inválida — posible alteración'}
                </div>
                <div style={{ fontSize: '.75rem', color: resultado.firma_ok ? '#86efac' : '#fde68a', lineHeight: 1.6 }}>
                  {resultado.firma_ok
                    ? 'La firma coincide exactamente con la generada al momento del pago. Nadie modificó este comprobante.'
                    : 'La firma no coincide con la original. Esto ocurre si el payload fue alterado o si la firma fue copiada incorrectamente. En un sistema bancario real, esta transacción sería rechazada automáticamente.'
                  }
                </div>
              </div>

              {/* Explicación del rol de cada mecanismo */}
              <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
                <div style={{ flex: 1, background: '#0a0a15', borderRadius: 8, padding: '10px 12px', border: '1px solid #1e1e3a', fontSize: '.72rem', lineHeight: 1.6 }}>
                  <div style={{ color: '#60a5fa', fontWeight: 700, marginBottom: 4 }}>AES-256 → Confidencialidad</div>
                  <div style={{ color: '#6b7280' }}>Cifra los datos para que nadie pueda <em>leerlos</em> sin la clave del servidor.</div>
                  <div style={{ color: resultado.integro ? '#4ade80' : '#fbbf24', marginTop: 4, fontWeight: 600 }}>
                    {resultado.datos && Object.keys(resultado.datos).length > 0 ? '✓ Descifrado exitoso' : '✗ No se pudo descifrar'}
                  </div>
                </div>
                <div style={{ flex: 1, background: '#0a0a15', borderRadius: 8, padding: '10px 12px', border: '1px solid #1e1e3a', fontSize: '.72rem', lineHeight: 1.6 }}>
                  <div style={{ color: '#a78bfa', fontWeight: 700, marginBottom: 4 }}>HMAC-SHA256 → Integridad</div>
                  <div style={{ color: '#6b7280' }}>Detecta si alguien <em>modificó</em> el payload después de emitirse.</div>
                  <div style={{ color: resultado.firma_ok ? '#4ade80' : '#f87171', marginTop: 4, fontWeight: 600 }}>
                    {resultado.firma_ok ? '✓ Firma válida' : '✗ Firma inválida'}
                  </div>
                </div>
              </div>

              {/* Datos descifrados */}
              {resultado.datos && Object.keys(resultado.datos).length > 0 && (
                <div style={{ background: '#0a0a15', borderRadius: 12, padding: 14, border: `1px solid ${resultado.firma_ok ? '#1e1e3a' : 'rgba(234,179,8,.2)'}` }}>
                  <div style={{ fontSize: '.72rem', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '.04em', marginBottom: 10, display: 'flex', justifyContent: 'space-between' }}>
                    <span>Datos descifrados (AES-256)</span>
                    {!resultado.firma_ok && <span style={{ color: '#fbbf24' }}>⚠ Verificar autenticidad</span>}
                  </div>
                  {Object.entries(resultado.datos)
                    .filter(([k]) => CAMPO_LABELS[k])
                    .map(([k, v]) => (
                      <div key={k} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', padding: '6px 0', borderBottom: '1px solid #1a1a2e' }}>
                        <span style={{ fontSize: '.75rem', color: '#6b7280', flexShrink: 0, marginRight: 12 }}>
                          {CAMPO_LABELS[k]}
                        </span>
                        <span style={{ fontSize: '.8rem', color: '#e5e5e5', fontFamily: 'monospace', textAlign: 'right', wordBreak: 'break-all' }}>
                          {k === 'ultimos_digitos' ? `**** **** **** ${v}` : String(v)}
                        </span>
                      </div>
                    ))}
                </div>
              )}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
