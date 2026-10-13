import { useState } from 'react'
import Dialog from '@mui/material/Dialog'
import DialogContent from '@mui/material/DialogContent'
import IconButton from '@mui/material/IconButton'
import CloseIcon from '@mui/icons-material/Close'
import { descifrarHistorialXML } from '../../api/historial'

const REACCION_EMOJI = {
  'Me encantó':    '❤️',
  'Me gustó':      '👍',
  'No me gustó':   '👎',
}

export default function HistorialDecryptModal({ open, onClose }) {
  const [xml, setXml]         = useState('')
  const [resultado, setResult] = useState(null)
  const [loading, setLoading]  = useState(false)
  const [error, setError]      = useState('')

  const handleClose = () => {
    setXml('')
    setResult(null)
    setError('')
    onClose()
  }

  const handleDescifrar = async () => {
    if (!xml.trim()) { setError('Pega el contenido del XML primero'); return }
    setError('')
    setResult(null)
    setLoading(true)
    try {
      const data = await descifrarHistorialXML(xml.trim())
      setResult(data)
    } catch (err) {
      const msg = err?.response?.data?.error || 'Error al descifrar el XML'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          background: '#12121f',
          border: '1px solid #1e1e3a',
          borderRadius: '20px',
          color: '#e5e5e5',
          boxShadow: '0 25px 60px rgba(0,0,0,.8)',
        },
      }}
    >
      <DialogContent sx={{ p: 0 }}>

        {/* Header */}
        <div style={{
          padding: '18px 22px 14px',
          borderBottom: '1px solid #1a1a2e',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: '1rem', color: '#f0f0f0' }}>
              Descifrar historial XML
            </div>
            <div style={{ fontSize: '.75rem', color: '#6b7280', marginTop: 2 }}>
              Pega el contenido del archivo XML descargado para ver tus registros
            </div>
          </div>
          <IconButton onClick={handleClose} size="small" sx={{ color: '#6b7280', '&:hover': { color: '#e5e5e5' } }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </div>

        <div style={{ padding: '18px 22px 24px' }}>

          {/* Explicación académica */}
          <div style={{
            background: 'rgba(29,78,216,.06)', border: '1px solid rgba(29,78,216,.2)',
            borderRadius: 10, padding: '10px 14px', marginBottom: 16, fontSize: '.78rem',
            color: '#93c5fd', lineHeight: 1.6,
          }}>
            <strong>¿Cómo funciona?</strong> El XML fue cifrado campo por campo con{' '}
            <strong>AES-256-Fernet</strong>. Solo el servidor NEXFLIS puede descifrar los datos
            (la clave no viaja en el archivo). La firma <strong>HMAC-SHA256</strong> en el atributo{' '}
            <code style={{ background: '#1e2a3a', padding: '1px 5px', borderRadius: 4 }}>firma</code>{' '}
            garantiza que el documento no fue alterado.
          </div>

          {/* Textarea */}
          <label style={{ fontSize: '.72rem', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '.04em', display: 'block', marginBottom: 6 }}>
            Contenido del XML
          </label>
          <textarea
            value={xml}
            onChange={e => { setXml(e.target.value); setError(''); setResult(null) }}
            placeholder={'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE historial SYSTEM "nexflis-historial.dtd">\n<historial ...>'}
            rows={7}
            style={{
              width: '100%', background: '#0d0d1a', border: '1px solid #2a2a4a',
              color: '#d1d5db', borderRadius: 10, padding: '10px 13px',
              fontSize: '.78rem', fontFamily: 'monospace', resize: 'vertical',
              outline: 'none', boxSizing: 'border-box', lineHeight: 1.5,
            }}
            onFocus={e => e.target.style.borderColor = '#e50914'}
            onBlur={e => e.target.style.borderColor = '#2a2a4a'}
          />

          {/* Botón descifrar */}
          <button
            onClick={handleDescifrar}
            disabled={loading || !xml.trim()}
            style={{
              marginTop: 12,
              background: loading || !xml.trim()
                ? '#1f1f35'
                : 'linear-gradient(135deg,#e50914,#9b0000)',
              color: loading || !xml.trim() ? '#6b7280' : '#fff',
              border: 'none', borderRadius: 20, padding: '9px 22px',
              fontWeight: 700, fontSize: '.86rem',
              cursor: loading || !xml.trim() ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? 'Descifrando...' : '🔓 Descifrar XML'}
          </button>

          {/* Error */}
          {error && (
            <div style={{
              marginTop: 12,
              background: 'rgba(229,9,20,.08)', border: '1px solid rgba(229,9,20,.3)',
              color: '#f87171', padding: '9px 13px', borderRadius: 10, fontSize: '.82rem',
            }}>
              ⚠ {error}
            </div>
          )}

          {/* Resultado */}
          {resultado && (
            <div style={{ marginTop: 20 }}>

              {/* Metadata + firma */}
              <div style={{
                display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 14,
              }}>
                <MetaBadge label="Titular"  value={resultado.titular} />
                <MetaBadge label="Generado" value={resultado.generado?.slice(0, 19).replace('T', ' ')} />
                <MetaBadge
                  label="Firma HMAC"
                  value={resultado.firma_ok ? '✓ Válida' : '✗ Inválida'}
                  color={resultado.firma_ok ? '#4ade80' : '#f87171'}
                  bg={resultado.firma_ok ? 'rgba(34,197,94,.07)' : 'rgba(229,9,20,.07)'}
                  border={resultado.firma_ok ? 'rgba(34,197,94,.3)' : 'rgba(229,9,20,.3)'}
                />
              </div>

              {!resultado.firma_ok && (
                <div style={{
                  background: 'rgba(229,9,20,.07)', border: '1px solid rgba(229,9,20,.25)',
                  borderRadius: 10, padding: '10px 14px', marginBottom: 14,
                  fontSize: '.78rem', color: '#f87171',
                }}>
                  ⚠ La firma HMAC no coincide — este archivo pudo haber sido modificado después de generarse.
                </div>
              )}

              {/* Tabla de registros */}
              {resultado.registros.length === 0 ? (
                <div style={{ color: '#6b7280', fontSize: '.85rem', textAlign: 'center', padding: '20px 0' }}>
                  Sin registros de visualización en este historial.
                </div>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '.82rem' }}>
                    <thead>
                      <tr style={{ background: '#0a0a15' }}>
                        {['#', 'Película', 'Reacción', 'Minutos', 'Fecha'].map(h => (
                          <th key={h} style={{
                            padding: '8px 10px', textAlign: 'left',
                            color: '#9ca3af', fontWeight: 600, fontSize: '.72rem',
                            textTransform: 'uppercase', letterSpacing: '.04em',
                            borderBottom: '1px solid #1a1a2e',
                          }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {resultado.registros.map((reg, i) => (
                        <tr
                          key={i}
                          style={{ background: i % 2 === 0 ? 'transparent' : '#0d0d1a' }}
                        >
                          <td style={tdStyle}>{i + 1}</td>
                          <td style={{ ...tdStyle, color: '#e5e5e5', fontWeight: 500 }}>{reg.pelicula}</td>
                          <td style={tdStyle}>
                            {REACCION_EMOJI[reg.reaccion] || ''} {reg.reaccion}
                          </td>
                          <td style={{ ...tdStyle, textAlign: 'center' }}>{reg.minutos} min</td>
                          <td style={{ ...tdStyle, color: '#9ca3af' }}>{reg.fecha}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

function MetaBadge({ label, value, color, bg, border }) {
  return (
    <div style={{
      background: bg || 'rgba(255,255,255,.04)',
      border: `1px solid ${border || '#2a2a4a'}`,
      borderRadius: 8, padding: '6px 12px',
    }}>
      <div style={{ fontSize: '.66rem', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '.04em', marginBottom: 2 }}>
        {label}
      </div>
      <div style={{ fontSize: '.82rem', color: color || '#e5e5e5', fontWeight: 600 }}>
        {value}
      </div>
    </div>
  )
}

const tdStyle = {
  padding: '8px 10px',
  color: '#9ca3af',
  borderBottom: '1px solid #1a1a2e',
  verticalAlign: 'middle',
}
