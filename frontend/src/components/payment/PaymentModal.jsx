import { useState } from 'react'
import Dialog from '@mui/material/Dialog'
import DialogContent from '@mui/material/DialogContent'
import IconButton from '@mui/material/IconButton'
import CloseIcon from '@mui/icons-material/Close'
import LockIcon from '@mui/icons-material/Lock'
import DownloadIcon from '@mui/icons-material/Download'
import VerifiedIcon from '@mui/icons-material/Verified'
import { pagar, descargarPDF, verificarTransaccion } from '../../api/payment'
import { useAuth } from '../../context/AuthContext'

// Formatea número de tarjeta con espacios cada 4 dígitos
function formatCard(val) {
  return val.replace(/\D/g, '').slice(0, 16).replace(/(.{4})/g, '$1 ').trim()
}
// Formatea fecha MM/AA
function formatExpiry(val) {
  const digits = val.replace(/\D/g, '').slice(0, 4)
  if (digits.length >= 3) return digits.slice(0, 2) + '/' + digits.slice(2)
  return digits
}

const inputS = {
  width: '100%', background: '#0d0d1a', border: '1px solid #2a2a4a',
  color: '#e5e5e5', borderRadius: 10, padding: '11px 14px',
  fontSize: '.9rem', outline: 'none', boxSizing: 'border-box',
  transition: 'border-color .2s', fontFamily: 'monospace',
}
const labelS = {
  fontSize: '.72rem', color: '#6b7280', display: 'block',
  marginBottom: 5, textTransform: 'uppercase', letterSpacing: '.04em',
}

export default function PaymentModal({ open, onClose }) {
  const { user, setUser } = useAuth()

  // Pasos: 'form' | 'success' | 'verify'
  const [step, setStep] = useState('form')

  // Campos del formulario
  const [numero, setNumero]   = useState('')
  const [titular, setTitular] = useState('')
  const [expiry, setExpiry]   = useState('')
  const [cvv, setCvv]         = useState('')

  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')
  const [txnResult, setTxnResult] = useState(null)

  // Estado de verificación
  const [verificando, setVerificando]   = useState(false)
  const [verificacion, setVerificacion] = useState(null)

  const handleClose = () => {
    setStep('form'); setNumero(''); setTitular(''); setExpiry(''); setCvv('')
    setError(''); setTxnResult(null); setVerificacion(null)
    onClose()
  }

  const handlePagar = async (e) => {
    e.preventDefault()
    setError('')
    const digits = numero.replace(/\s/g, '')
    if (digits.length < 13) { setError('Número de tarjeta inválido'); return }
    if (!titular.trim())    { setError('Ingresa el nombre del titular'); return }
    if (expiry.length < 5)  { setError('Fecha de vencimiento inválida'); return }
    if (cvv.length < 3)     { setError('CVV inválido'); return }

    setLoading(true)
    try {
      const data = await pagar(digits)
      // Actualizar plan en contexto
      setUser(prev => ({ ...prev, plan: 'premium', plan_expires_at: data.expires_at }))
      setTxnResult(data)
      setStep('success')
    } catch (err) {
      setError(err?.response?.data?.error || 'Error al procesar el pago')
    } finally {
      setLoading(false)
    }
  }

  const handleVerificar = async () => {
    if (!txnResult?.txn_id) return
    setVerificando(true)
    try {
      const v = await verificarTransaccion(txnResult.txn_id)
      setVerificacion(v)
      setStep('verify')
    } catch {
      setVerificacion({ firma_ok: false, mensaje: 'Error al verificar' })
      setStep('verify')
    } finally {
      setVerificando(false)
    }
  }

  // Color de la tarjeta visual según primeros dígitos
  const cardGradient = () => {
    const d = numero.replace(/\s/g, '')[0]
    if (d === '4') return 'linear-gradient(135deg,#1a1a6e,#3b82f6)'  // Visa
    if (d === '5') return 'linear-gradient(135deg,#7b0a0a,#e50914)'  // Mastercard
    if (d === '3') return 'linear-gradient(135deg,#14532d,#16a34a)'  // Amex
    return 'linear-gradient(135deg,#1e1e3a,#4a4a8a)'
  }

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="xs"
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
        <div style={{ padding: '20px 22px 16px', borderBottom: '1px solid #1a1a2e', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: '1rem', color: '#f0f0f0' }}>
              {step === 'form'    && 'Actualizar a Premium'}
              {step === 'success' && '¡Pago aprobado!'}
              {step === 'verify'  && 'Verificación de comprobante'}
            </div>
            <div style={{ fontSize: '.75rem', color: '#6b7280', marginTop: 2 }}>
              {step === 'form' && <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><LockIcon sx={{ fontSize: '.85rem' }} /> Pago simulado — entorno seguro</span>}
              {step === 'success' && `ID: ${txnResult?.txn_id}`}
              {step === 'verify'  && `ID: ${txnResult?.txn_id}`}
            </div>
          </div>
          <IconButton onClick={handleClose} size="small" sx={{ color: '#6b7280', '&:hover': { color: '#e5e5e5' } }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </div>

        {/* ── PASO 1: FORMULARIO DE PAGO ── */}
        {step === 'form' && (
          <div style={{ padding: '18px 22px 24px' }}>

            {/* Plan info */}
            <div style={{ background: 'linear-gradient(135deg,#1a0a0a,#2d0f0f)', border: '1px solid #7b0a0a', borderRadius: 12, padding: '14px 16px', marginBottom: 20 }}>
              <div style={{ fontSize: '.78rem', color: '#f87171', textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 6 }}>Plan Premium</div>
              <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#fff' }}>$99.99 <span style={{ fontSize: '.9rem', color: '#9ca3af', fontWeight: 400 }}>MXN / mes</span></div>
              <div style={{ fontSize: '.8rem', color: '#d1d5db', marginTop: 6, lineHeight: 1.6 }}>
                ✓ Recomendaciones ilimitadas &nbsp;·&nbsp; ✓ Calidad 4K &nbsp;·&nbsp; ✓ Sin anuncios
              </div>
            </div>

            {/* Tarjeta visual */}
            <div style={{ background: cardGradient(), borderRadius: 14, padding: '18px 20px', marginBottom: 20, minHeight: 90, position: 'relative', boxShadow: '0 8px 24px rgba(0,0,0,.4)' }}>
              <div style={{ fontSize: '.7rem', color: 'rgba(255,255,255,.6)', marginBottom: 12, letterSpacing: '.1em' }}>NEXFLIS CARD</div>
              <div style={{ fontSize: '1.05rem', fontFamily: 'monospace', color: '#fff', letterSpacing: '.15em', marginBottom: 14 }}>
                {numero || '**** **** **** ****'}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '.72rem', color: 'rgba(255,255,255,.7)' }}>
                <span>{titular.toUpperCase() || 'NOMBRE DEL TITULAR'}</span>
                <span>{expiry || 'MM/AA'}</span>
              </div>
            </div>

            <form onSubmit={handlePagar}>
              <div style={{ marginBottom: 14 }}>
                <label style={labelS}>Número de tarjeta</label>
                <input
                  style={inputS} value={numero} placeholder="1234 5678 9012 3456"
                  onChange={e => setNumero(formatCard(e.target.value))}
                  maxLength={19} inputMode="numeric"
                  onFocus={e => e.target.style.borderColor = '#e50914'}
                  onBlur={e => e.target.style.borderColor = '#2a2a4a'}
                />
              </div>
              <div style={{ marginBottom: 14 }}>
                <label style={labelS}>Nombre del titular</label>
                <input
                  style={{ ...inputS, fontFamily: 'inherit', textTransform: 'uppercase' }}
                  value={titular} placeholder="COMO APARECE EN LA TARJETA"
                  onChange={e => setTitular(e.target.value)}
                  onFocus={e => e.target.style.borderColor = '#e50914'}
                  onBlur={e => e.target.style.borderColor = '#2a2a4a'}
                />
              </div>
              <div style={{ display: 'flex', gap: 12, marginBottom: 14 }}>
                <div style={{ flex: 1 }}>
                  <label style={labelS}>Vencimiento</label>
                  <input
                    style={inputS} value={expiry} placeholder="MM/AA"
                    onChange={e => setExpiry(formatExpiry(e.target.value))}
                    maxLength={5} inputMode="numeric"
                    onFocus={e => e.target.style.borderColor = '#e50914'}
                    onBlur={e => e.target.style.borderColor = '#2a2a4a'}
                  />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={labelS}>CVV</label>
                  <input
                    style={inputS} value={cvv} placeholder="123"
                    onChange={e => setCvv(e.target.value.replace(/\D/g, '').slice(0, 4))}
                    maxLength={4} inputMode="numeric" type="password"
                    onFocus={e => e.target.style.borderColor = '#e50914'}
                    onBlur={e => e.target.style.borderColor = '#2a2a4a'}
                  />
                </div>
              </div>

              {error && (
                <div style={{ background: 'rgba(229,9,20,.08)', border: '1px solid rgba(229,9,20,.3)', color: '#f87171', padding: '8px 12px', borderRadius: 10, fontSize: '.82rem', marginBottom: 14 }}>
                  ⚠ {error}
                </div>
              )}

              <button
                type="submit" disabled={loading}
                style={{
                  width: '100%', padding: '13px',
                  background: loading ? '#1f1f35' : 'linear-gradient(135deg,#e50914,#9b0000)',
                  color: loading ? '#6b7280' : '#fff', border: 'none', borderRadius: 30,
                  fontWeight: 700, fontSize: '.95rem', cursor: loading ? 'not-allowed' : 'pointer',
                }}
              >
                {loading ? 'Procesando...' : `Pagar $99.99 MXN`}
              </button>

              <div style={{ textAlign: 'center', fontSize: '.72rem', color: '#4b5563', marginTop: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}>
                <LockIcon sx={{ fontSize: '.8rem' }} /> Simulación educativa · Los datos de tarjeta no se almacenan
              </div>
            </form>
          </div>
        )}

        {/* ── PASO 2: ÉXITO ── */}
        {step === 'success' && txnResult && (
          <div style={{ padding: '24px 22px' }}>
            <div style={{ textAlign: 'center', marginBottom: 22 }}>
              <div style={{ fontSize: '2.5rem', marginBottom: 8 }}>🎉</div>
              <div style={{ fontWeight: 700, fontSize: '1.1rem', color: '#4ade80', marginBottom: 4 }}>¡Bienvenido a Premium!</div>
              <div style={{ fontSize: '.82rem', color: '#9ca3af' }}>Tu plan está activo por 30 días</div>
            </div>

            {/* Resumen */}
            <div style={{ background: '#0a0a15', borderRadius: 12, padding: 16, marginBottom: 20, border: '1px solid #1e1e3a' }}>
              {[
                ['ID de transacción', txnResult.txn_id],
                ['Plan', 'NEXFLIS Premium'],
                ['Monto', '$99.99 MXN (simulado)'],
                ['Vigencia', new Date(txnResult.expires_at).toLocaleDateString('es-MX', { day:'2-digit', month:'long', year:'numeric' })],
              ].map(([k, v]) => (
                <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #1a1a2e', fontSize: '.83rem' }}>
                  <span style={{ color: '#6b7280' }}>{k}</span>
                  <span style={{ color: '#e5e5e5', fontWeight: 500, fontFamily: k === 'ID de transacción' ? 'monospace' : 'inherit' }}>{v}</span>
                </div>
              ))}
            </div>

            {/* Explicación educativa */}
            <div style={{ background: 'rgba(29,78,216,.08)', border: '1px solid rgba(29,78,216,.3)', borderRadius: 10, padding: '12px 14px', marginBottom: 18, fontSize: '.78rem', color: '#93c5fd', lineHeight: 1.6 }}>
              <strong>¿Qué pasó internamente?</strong><br />
              Los datos de tu transacción fueron <strong>cifrados con AES-256</strong> y se generó una <strong>firma HMAC-SHA256</strong> para garantizar que nadie pueda alterarlos. El comprobante PDF contiene los datos visibles y el payload cifrado — igual que un comprobante bancario real.
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <button
                onClick={() => descargarPDF(txnResult.txn_id)}
                style={{ width: '100%', padding: '11px', background: 'linear-gradient(135deg,#e50914,#9b0000)', color: '#fff', border: 'none', borderRadius: 30, fontWeight: 700, fontSize: '.88rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}
              >
                <DownloadIcon sx={{ fontSize: '1rem' }} /> Descargar comprobante PDF
              </button>
              <button
                onClick={handleVerificar} disabled={verificando}
                style={{ width: '100%', padding: '11px', background: 'transparent', color: '#93c5fd', border: '1px solid rgba(29,78,216,.4)', borderRadius: 30, fontWeight: 600, fontSize: '.88rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}
              >
                <VerifiedIcon sx={{ fontSize: '1rem' }} /> {verificando ? 'Verificando...' : 'Verificar integridad'}
              </button>
              <button
                onClick={handleClose}
                style={{ width: '100%', padding: '11px', background: 'transparent', color: '#6b7280', border: '1px solid #2a2a4a', borderRadius: 30, fontWeight: 600, fontSize: '.88rem', cursor: 'pointer' }}
              >
                Cerrar
              </button>
            </div>
          </div>
        )}

        {/* ── PASO 3: VERIFICACIÓN ── */}
        {step === 'verify' && verificacion && (
          <div style={{ padding: '20px 22px 24px' }}>
            <div style={{ textAlign: 'center', marginBottom: 18 }}>
              <div style={{ fontSize: '2rem', marginBottom: 6 }}>{verificacion.firma_ok ? '✅' : '❌'}</div>
              <div style={{ fontWeight: 700, fontSize: '.95rem', color: verificacion.firma_ok ? '#4ade80' : '#f87171' }}>
                {verificacion.mensaje}
              </div>
            </div>

            {verificacion.datos && (
              <div style={{ background: '#0a0a15', borderRadius: 12, padding: 14, border: '1px solid #1e1e3a', marginBottom: 16 }}>
                <div style={{ fontSize: '.72rem', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '.04em', marginBottom: 10 }}>Datos descifrados (AES-256)</div>
                {Object.entries(verificacion.datos)
                  .filter(([k]) => !['payload_cifrado'].includes(k))
                  .map(([k, v]) => (
                    <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid #1a1a2e', fontSize: '.78rem' }}>
                      <span style={{ color: '#6b7280', fontFamily: 'monospace' }}>{k}</span>
                      <span style={{ color: '#e5e5e5', maxWidth: '55%', textAlign: 'right', wordBreak: 'break-all', fontFamily: 'monospace' }}>{String(v)}</span>
                    </div>
                  ))}
              </div>
            )}

            <div style={{ background: 'rgba(29,78,216,.08)', border: '1px solid rgba(29,78,216,.25)', borderRadius: 10, padding: '10px 14px', marginBottom: 16, fontSize: '.76rem', color: '#93c5fd', lineHeight: 1.6 }}>
              <strong>¿Cómo funciona?</strong> El servidor descifra el payload con AES-256 y recalcula la firma HMAC-SHA256. Si coincide con la firma guardada al momento del pago, el comprobante es auténtico. Este es el mismo principio que usan SWIFT y los bancos para verificar transferencias.
            </div>

            <div style={{ display: 'flex', gap: 10 }}>
              <button
                onClick={() => setStep('success')}
                style={{ flex: 1, padding: '10px', background: 'transparent', color: '#9ca3af', border: '1px solid #2a2a4a', borderRadius: 30, fontWeight: 600, fontSize: '.86rem', cursor: 'pointer' }}
              >
                ← Volver
              </button>
              <button
                onClick={() => descargarPDF(txnResult.txn_id)}
                style={{ flex: 1, padding: '10px', background: 'linear-gradient(135deg,#e50914,#9b0000)', color: '#fff', border: 'none', borderRadius: 30, fontWeight: 700, fontSize: '.86rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
              >
                <DownloadIcon sx={{ fontSize: '.9rem' }} /> PDF
              </button>
            </div>
          </div>
        )}

      </DialogContent>
    </Dialog>
  )
}
