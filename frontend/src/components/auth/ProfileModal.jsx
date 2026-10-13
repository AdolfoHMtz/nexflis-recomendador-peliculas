import { useState, useEffect, useRef } from 'react'
import Dialog from '@mui/material/Dialog'
import DialogContent from '@mui/material/DialogContent'
import IconButton from '@mui/material/IconButton'
import CloseIcon from '@mui/icons-material/Close'
import EditIcon from '@mui/icons-material/Edit'
import VisibilityIcon from '@mui/icons-material/Visibility'
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff'
import { updateProfile, getMe, deleteAccount } from '../../api/auth'
import { descargarUltimoPDF } from '../../api/payment'
import { descargarHistorialPDF, descargarHistorialXML } from '../../api/historial'
import { useAuth } from '../../context/AuthContext'
import PaymentModal from '../payment/PaymentModal'
import VerifyModal from '../payment/VerifyModal'
import HistorialDecryptModal from '../payment/HistorialDecryptModal'

function PasswordInput({ value, onChange, placeholder, inputRef }) {
  const [show, setShow] = useState(false)
  return (
    <div style={{ position: 'relative' }}>
      <input
        ref={inputRef}
        type={show ? 'text' : 'password'}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        autoComplete="new-password"
        name={`pw_${Math.random()}`}
        style={{
          width: '100%', background: '#0d0d1a', border: '1px solid #2a2a4a',
          color: '#e5e5e5', borderRadius: 10, padding: '10px 40px 10px 13px',
          fontSize: '.88rem', outline: 'none', boxSizing: 'border-box',
          transition: 'border-color .2s',
        }}
        onFocus={e => e.target.style.borderColor = '#e50914'}
        onBlur={e => e.target.style.borderColor = '#2a2a4a'}
      />
      <button
        type="button"
        onClick={() => setShow(s => !s)}
        style={{
          position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
          background: 'none', border: 'none', color: '#6b7280', cursor: 'pointer',
          display: 'flex', alignItems: 'center', padding: 0,
        }}
      >
        {show ? <VisibilityOffIcon sx={{ fontSize: '1rem' }} /> : <VisibilityIcon sx={{ fontSize: '1rem' }} />}
      </button>
    </div>
  )
}

function InfoRow({ label, value, onEdit }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '12px 0', borderBottom: '1px solid #1a1a2e',
    }}>
      <div>
        <div style={{ fontSize: '.72rem', color: '#4b5563', textTransform: 'uppercase', letterSpacing: '.04em', marginBottom: 3 }}>
          {label}
        </div>
        <div style={{ fontSize: '.92rem', color: value ? '#e5e5e5' : '#6b7280', fontWeight: value ? 500 : 400 }}>
          {value || <span style={{ fontStyle: 'italic' }}>Sin configurar</span>}
        </div>
      </div>
      <button
        type="button"
        onClick={onEdit}
        style={{
          background: 'none', border: '1px solid #2a2a4a', color: '#9ca3af',
          borderRadius: 8, padding: '5px 11px', fontSize: '.75rem', cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: 5,
          transition: 'border-color .2s, color .2s',
        }}
        onMouseEnter={e => { e.currentTarget.style.borderColor = '#e50914'; e.currentTarget.style.color = '#e5e5e5' }}
        onMouseLeave={e => { e.currentTarget.style.borderColor = '#2a2a4a'; e.currentTarget.style.color = '#9ca3af' }}
      >
        <EditIcon sx={{ fontSize: '.8rem' }} /> Editar
      </button>
    </div>
  )
}

const inputStyle = {
  width: '100%', background: '#0d0d1a', border: '1px solid #2a2a4a',
  color: '#e5e5e5', borderRadius: 10, padding: '10px 13px',
  fontSize: '.88rem', outline: 'none', boxSizing: 'border-box',
  transition: 'border-color .2s',
}

export default function ProfileModal({ open, onClose }) {
  const { user, setUser, logout } = useAuth()

  const [mode, setMode] = useState('view')
  const [paymentOpen, setPaymentOpen]         = useState(false)
  const [verifyOpen, setVerifyOpen]           = useState(false)
  const [deleteOpen, setDeleteOpen]           = useState(false)
  const [histDecryptOpen, setHistDecryptOpen] = useState(false)
  const [histLoading, setHistLoading]         = useState({ pdf: false, xml: false })
  const [editingField, setEditingField] = useState(null)

  // Estado para borrar cuenta
  const [deletePw, setDeletePw]         = useState('')
  const [deleteError, setDeleteError]   = useState('')
  const [deleteLoading, setDeleteLoading] = useState(false)

  const [username, setUsername] = useState('')
  const [email, setEmail]       = useState('')
  const [edad, setEdad]         = useState('')

  // Solo se usan cuando editingField === 'password'
  const [passwordNueva, setPasswordNueva]               = useState('')
  const [passwordNuevaConfirm, setPasswordNuevaConfirm] = useState('')

  // Siempre requerida para guardar — ref para limpiarla programáticamente
  const [passwordConfirmacion, setPasswordConfirmacion] = useState('')
  const pwConfirmRef = useRef(null)

  const [error, setError]     = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)

  const resetToView = (userData) => {
    const u = userData || user
    if (u) {
      setUsername(u.username || '')
      setEmail(u.email || '')
      setEdad(u.edad != null ? String(u.edad) : '')
    }
    setPasswordConfirmacion('')
    setPasswordNueva('')
    setPasswordNuevaConfirm('')
    // Limpiar el DOM del input directamente para que el browser no recuerde el valor
    if (pwConfirmRef.current) pwConfirmRef.current.value = ''
    setEditingField(null)
    setError('')
    setSuccess('')
    setMode('view')
  }

  useEffect(() => {
    if (!open) return
    if (user && user.email == null) {
      getMe().then(data => {
        if (data.authenticated) {
          setUser(prev => ({ ...prev, email: data.email }))
          resetToView(data)
        } else {
          resetToView()
        }
      }).catch(() => resetToView())
    } else {
      resetToView()
    }
  }, [open, user?.id])

  const enterEdit = (field) => {
    setEditingField(field)
    setPasswordConfirmacion('')
    if (pwConfirmRef.current) pwConfirmRef.current.value = ''
    setPasswordNueva('')
    setPasswordNuevaConfirm('')
    setError('')
    setSuccess('')
    setMode('edit')
  }

  const handleCancel = () => resetToView()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    if (!passwordConfirmacion) {
      setError('Ingresa tu contraseña actual para confirmar')
      return
    }

    const payload = { password_actual: passwordConfirmacion }
    let hayCambios = false

    if (editingField === 'username') {
      const newUsername = username.trim()
      if (!newUsername) { setError('El usuario no puede estar vacío'); return }
      if (newUsername.length < 3) { setError('El usuario debe tener al menos 3 caracteres'); return }
      if (newUsername !== user.username) { payload.username = newUsername; hayCambios = true }
    }

    if (editingField === 'email') {
      const newEmail = email.trim()
      if (newEmail && !newEmail.includes('@')) { setError('Email inválido'); return }
      if (newEmail !== (user.email || '')) { payload.email = newEmail; hayCambios = true }
    }

    if (editingField === 'edad') {
      if (!edad) { setError('Ingresa una edad'); return }
      const edadNum = parseInt(edad, 10)
      if (isNaN(edadNum) || edadNum < 1 || edadNum > 120) { setError('Edad inválida (1–120)'); return }
      if (edadNum !== user.edad) { payload.edad = edadNum; hayCambios = true }
    }

    if (editingField === 'password') {
      if (!passwordNueva) { setError('Ingresa la nueva contraseña'); return }
      if (passwordNueva.length < 6) { setError('La nueva contraseña debe tener al menos 6 caracteres'); return }
      if (passwordNueva !== passwordNuevaConfirm) { setError('Las nuevas contraseñas no coinciden'); return }
      if (passwordNueva === passwordConfirmacion) { setError('La nueva contraseña debe ser diferente a la actual'); return }
      payload.password = passwordNueva
      hayCambios = true
    }

    if (!hayCambios) { setError('No hay cambios para guardar'); return }

    setLoading(true)
    try {
      const updated = await updateProfile(payload)
      setUser(prev => ({
        ...prev,
        username: updated.username,
        email:    updated.email,
        edad:     updated.edad,
        needs_age: updated.edad == null,
      }))
      setSuccess('Perfil actualizado')
      setMode('view')
      setEditingField(null)
      setPasswordConfirmacion('')
      setPasswordNueva('')
      setPasswordNuevaConfirm('')
      if (pwConfirmRef.current) pwConfirmRef.current.value = ''
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      const msg = err?.response?.data?.error || 'No se pudo actualizar el perfil'
      if (msg.toLowerCase().includes('actual') || msg.toLowerCase().includes('incorrecta')) {
        setError('Contraseña actual incorrecta')
      } else if (msg.toLowerCase().includes('uso') || msg.toLowerCase().includes('registrado')) {
        setError('El usuario o email ya está en uso')
      } else {
        setError(msg)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
    <Dialog
      open={open}
      onClose={() => { resetToView(); onClose() }}
      maxWidth="xs"
      fullWidth
      PaperProps={{
        sx: {
          background: '#12121f',
          border: '1px solid #1e1e3a',
          borderRadius: '20px',
          color: '#e5e5e5',
          boxShadow: '0 25px 60px rgba(0,0,0,.7)',
        },
      }}
    >
      <DialogContent sx={{ p: 0 }}>

        {/* Header */}
        <div style={{
          padding: '20px 22px 16px',
          borderBottom: '1px solid #1a1a2e',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <div style={{ fontWeight: 700, fontSize: '1rem', color: '#f0f0f0' }}>
            {mode === 'view' ? 'Mi perfil' : 'Editar perfil'}
          </div>
          <IconButton
            onClick={() => { resetToView(); onClose() }}
            size="small"
            sx={{ color: '#6b7280', '&:hover': { color: '#e5e5e5' } }}
          >
            <CloseIcon fontSize="small" />
          </IconButton>
        </div>

        {/* Avatar */}
        <div style={{ display: 'flex', justifyContent: 'center', padding: '20px 0 6px' }}>
          <div style={{
            width: 60, height: 60, borderRadius: '50%',
            background: 'linear-gradient(135deg,#e50914,#7b0a0a)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '1.5rem', fontWeight: 700, color: '#fff',
            boxShadow: '0 0 0 3px #1a1a2e',
          }}>
            {(user?.username?.[0] || '?').toUpperCase()}
          </div>
        </div>

        {/* ── MODO VISTA ── */}
        {mode === 'view' && (
          <div style={{ padding: '8px 22px 22px' }}>
            <InfoRow label="Usuario"    value={user?.username} onEdit={() => enterEdit('username')} />
            <InfoRow label="Email"      value={user?.email}    onEdit={() => enterEdit('email')} />
            <InfoRow label="Edad"       value={user?.edad != null ? `${user.edad} años` : null} onEdit={() => enterEdit('edad')} />
            <InfoRow label="Contraseña" value="••••••••"       onEdit={() => enterEdit('password')} />

            {/* Plan */}
            <div style={{ marginTop: 16, padding: '14px 16px', borderRadius: 12, background: user?.plan === 'premium' ? 'rgba(229,9,20,.07)' : '#0a0a15', border: `1px solid ${user?.plan === 'premium' ? 'rgba(229,9,20,.35)' : '#1e1e3a'}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: '.72rem', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '.04em', marginBottom: 4 }}>Plan actual</div>
                  <div style={{ fontWeight: 700, fontSize: '.95rem', color: user?.plan === 'premium' ? '#e50914' : '#9ca3af' }}>
                    {user?.plan === 'premium' ? '⭐ Premium' : 'Free'}
                  </div>
                  {user?.plan === 'premium' && user?.plan_expires_at && (
                    <div style={{ fontSize: '.72rem', color: '#6b7280', marginTop: 3 }}>
                      Vence: {new Date(user.plan_expires_at).toLocaleDateString('es-MX', { day: '2-digit', month: 'long', year: 'numeric' })}
                    </div>
                  )}
                </div>
                {user?.plan !== 'premium' ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'flex-end' }}>
                    <button
                      onClick={() => setPaymentOpen(true)}
                      style={{ background: 'linear-gradient(135deg,#e50914,#9b0000)', color: '#fff', border: 'none', borderRadius: 20, padding: '7px 14px', fontSize: '.78rem', fontWeight: 700, cursor: 'pointer', whiteSpace: 'nowrap' }}
                    >
                      Actualizar a Premium
                    </button>
                    <button
                      onClick={() => setVerifyOpen(true)}
                      style={{ background: 'transparent', color: '#6b7280', border: 'none', fontSize: '.72rem', cursor: 'pointer', padding: 0, textDecoration: 'underline' }}
                    >
                      Verificar comprobante
                    </button>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'flex-end' }}>
                    <button
                      onClick={() => descargarUltimoPDF()}
                      style={{ background: 'linear-gradient(135deg,#e50914,#9b0000)', color: '#fff', border: 'none', borderRadius: 20, padding: '7px 14px', fontSize: '.78rem', fontWeight: 700, cursor: 'pointer', whiteSpace: 'nowrap' }}
                    >
                      Descargar comprobante
                    </button>
                    <button
                      onClick={() => setVerifyOpen(true)}
                      style={{ background: 'transparent', color: '#9ca3af', border: 'none', fontSize: '.72rem', cursor: 'pointer', padding: 0, textDecoration: 'underline' }}
                    >
                      Verificar comprobante
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Historial exportable */}
            <div style={{ marginTop: 16, padding: '14px 16px', borderRadius: 12, background: '#0a0a15', border: '1px solid #1e1e3a' }}>
              <div style={{ fontSize: '.72rem', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '.04em', marginBottom: 10 }}>
                Historial de visualizaciones
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button
                  onClick={async () => {
                    setHistLoading(s => ({ ...s, pdf: true }))
                    try { await descargarHistorialPDF(user?.username) } catch { /* silencioso */ }
                    finally { setHistLoading(s => ({ ...s, pdf: false })) }
                  }}
                  disabled={histLoading.pdf}
                  style={{
                    background: histLoading.pdf ? '#1f1f35' : 'linear-gradient(135deg,#e50914,#9b0000)',
                    color: histLoading.pdf ? '#6b7280' : '#fff',
                    border: 'none', borderRadius: 20, padding: '7px 14px',
                    fontSize: '.78rem', fontWeight: 700, cursor: histLoading.pdf ? 'not-allowed' : 'pointer',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {histLoading.pdf ? 'Generando...' : '📄 Descargar PDF'}
                </button>
                <button
                  onClick={async () => {
                    setHistLoading(s => ({ ...s, xml: true }))
                    try { await descargarHistorialXML(user?.username) } catch { /* silencioso */ }
                    finally { setHistLoading(s => ({ ...s, xml: false })) }
                  }}
                  disabled={histLoading.xml}
                  style={{
                    background: histLoading.xml ? '#1f1f35' : 'linear-gradient(135deg,#1d4ed8,#1e3a8a)',
                    color: histLoading.xml ? '#6b7280' : '#fff',
                    border: 'none', borderRadius: 20, padding: '7px 14px',
                    fontSize: '.78rem', fontWeight: 700, cursor: histLoading.xml ? 'not-allowed' : 'pointer',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {histLoading.xml ? 'Generando...' : '🔐 Descargar XML cifrado'}
                </button>
                <button
                  onClick={() => setHistDecryptOpen(true)}
                  style={{
                    background: 'transparent', color: '#9ca3af',
                    border: '1px solid #2a2a4a', borderRadius: 20, padding: '7px 14px',
                    fontSize: '.78rem', fontWeight: 600, cursor: 'pointer', whiteSpace: 'nowrap',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = '#4a4a6a'; e.currentTarget.style.color = '#e5e5e5' }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = '#2a2a4a'; e.currentTarget.style.color = '#9ca3af' }}
                >
                  🔓 Descifrar XML
                </button>
              </div>
            </div>

            {success && (
              <div style={{
                marginTop: 14,
                background: 'rgba(34,197,94,.08)', border: '1px solid rgba(34,197,94,.3)',
                color: '#4ade80', padding: '9px 13px', borderRadius: 10,
                fontSize: '.82rem', display: 'flex', alignItems: 'center', gap: 8,
              }}>
                <span>✓</span> {success}
              </div>
            )}

            {/* Zona de peligro */}
            <div style={{ marginTop: 20, paddingTop: 16, borderTop: '1px solid #1a1a2e' }}>
              <button
                type="button"
                onClick={() => { setDeleteOpen(true); setDeleteError(''); setDeletePw('') }}
                style={{
                  background: 'none', border: 'none', color: '#6b7280',
                  fontSize: '.75rem', cursor: 'pointer', padding: 0,
                  textDecoration: 'underline', textUnderlineOffset: 3,
                }}
              >
                Eliminar cuenta
              </button>
            </div>
          </div>
        )}

        {/* ── MODO EDICIÓN ── */}
        {mode === 'edit' && (
          <form onSubmit={handleSubmit} style={{ padding: '14px 22px 22px' }}>

            {/* Campo activo según editingField */}
            <div style={{ marginBottom: 6 }}>
              <label style={{
                fontSize: '.72rem', color: '#e50914', display: 'block',
                marginBottom: 6, textTransform: 'uppercase', letterSpacing: '.04em',
              }}>
                {{ username: 'Usuario', email: 'Email', edad: 'Edad', password: 'Nueva contraseña' }[editingField]}
              </label>

              {editingField === 'username' && (
                <input
                  type="text"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  autoComplete="off"
                  style={inputStyle}
                  onFocus={e => e.target.style.borderColor = '#e50914'}
                  onBlur={e => e.target.style.borderColor = '#2a2a4a'}
                  autoFocus
                />
              )}

              {editingField === 'email' && (
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="tu@email.com"
                  autoComplete="off"
                  style={inputStyle}
                  onFocus={e => e.target.style.borderColor = '#e50914'}
                  onBlur={e => e.target.style.borderColor = '#2a2a4a'}
                  autoFocus
                />
              )}

              {editingField === 'edad' && (
                <input
                  type="number"
                  min="1" max="120"
                  value={edad}
                  onChange={e => setEdad(e.target.value)}
                  autoComplete="off"
                  style={{ ...inputStyle, width: '35%' }}
                  onFocus={e => e.target.style.borderColor = '#e50914'}
                  onBlur={e => e.target.style.borderColor = '#2a2a4a'}
                  autoFocus
                />
              )}

              {editingField === 'password' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <div>
                    <label style={{ fontSize: '.72rem', color: '#4b5563', display: 'block', marginBottom: 5 }}>
                      Nueva contraseña
                    </label>
                    <PasswordInput
                      value={passwordNueva}
                      onChange={e => setPasswordNueva(e.target.value)}
                      placeholder="Mínimo 6 caracteres"
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: '.72rem', color: '#4b5563', display: 'block', marginBottom: 5 }}>
                      Confirmar nueva contraseña
                    </label>
                    <PasswordInput
                      value={passwordNuevaConfirm}
                      onChange={e => setPasswordNuevaConfirm(e.target.value)}
                      placeholder="Repite la nueva contraseña"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Divider */}
            <div style={{ borderTop: '1px solid #1a1a2e', margin: '16px 0' }} />

            {/* Contraseña actual — siempre requerida, siempre vacía */}
            <div style={{ marginBottom: 16 }}>
              <label style={{
                fontSize: '.72rem', color: '#6b7280', display: 'block',
                marginBottom: 6, textTransform: 'uppercase', letterSpacing: '.04em',
              }}>
                Contraseña actual <span style={{ color: '#e50914' }}>*</span>
              </label>
              <PasswordInput
                value={passwordConfirmacion}
                onChange={e => setPasswordConfirmacion(e.target.value)}
                placeholder="Escribe tu contraseña para confirmar"
                inputRef={pwConfirmRef}
              />
            </div>

            {/* Feedback */}
            {error && (
              <div style={{
                background: 'rgba(229,9,20,.08)', border: '1px solid rgba(229,9,20,.3)',
                color: '#f87171', padding: '8px 12px', borderRadius: 10,
                fontSize: '.82rem', marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8,
              }}>
                <span>⚠</span> {error}
              </div>
            )}

            {/* Botones */}
            <div style={{ display: 'flex', gap: 10 }}>
              <button
                type="button"
                onClick={handleCancel}
                style={{
                  flex: 1, background: 'transparent', border: '1px solid #2a2a4a',
                  color: '#9ca3af', padding: '10px', borderRadius: 30,
                  fontWeight: 600, fontSize: '.86rem', cursor: 'pointer',
                }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = '#4a4a6a'; e.currentTarget.style.color = '#e5e5e5' }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = '#2a2a4a'; e.currentTarget.style.color = '#9ca3af' }}
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={loading}
                style={{
                  flex: 1,
                  background: loading ? '#1f1f35' : 'linear-gradient(135deg,#e50914,#9b0000)',
                  color: loading ? '#6b7280' : '#fff',
                  border: 'none', padding: '10px', borderRadius: 30,
                  fontWeight: 700, fontSize: '.86rem',
                  cursor: loading ? 'not-allowed' : 'pointer',
                }}
              >
                {loading ? 'Guardando...' : 'Guardar cambios'}
              </button>
            </div>
          </form>
        )}

      </DialogContent>
    </Dialog>

    <PaymentModal
      open={paymentOpen}
      onClose={() => setPaymentOpen(false)}
    />
    <VerifyModal
      open={verifyOpen}
      onClose={() => setVerifyOpen(false)}
    />
    <HistorialDecryptModal
      open={histDecryptOpen}
      onClose={() => setHistDecryptOpen(false)}
    />

    {/* ── Modal confirmar borrado ── */}
    <Dialog
      open={deleteOpen}
      onClose={() => !deleteLoading && setDeleteOpen(false)}
      maxWidth="xs"
      fullWidth
      PaperProps={{
        sx: {
          background: '#12121f', border: '1px solid #3a1a1a',
          borderRadius: '16px', color: '#e5e5e5',
          boxShadow: '0 25px 60px rgba(0,0,0,.8)',
        },
      }}
    >
      <DialogContent sx={{ p: 0 }}>
        <div style={{ padding: '22px 22px 24px' }}>
          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div style={{ fontWeight: 700, fontSize: '1rem', color: '#f87171' }}>Eliminar cuenta</div>
            <IconButton onClick={() => setDeleteOpen(false)} size="small" sx={{ color: '#6b7280' }} disabled={deleteLoading}>
              <CloseIcon fontSize="small" />
            </IconButton>
          </div>

          {/* Advertencia */}
          <div style={{ background: 'rgba(229,9,20,.07)', border: '1px solid rgba(229,9,20,.25)', borderRadius: 10, padding: '12px 14px', marginBottom: 18 }}>
            <div style={{ fontWeight: 700, fontSize: '.85rem', color: '#f87171', marginBottom: 6 }}>
              ⚠ Esta acción es permanente e irreversible
            </div>
            <div style={{ fontSize: '.78rem', color: '#9ca3af', lineHeight: 1.6 }}>
              Se eliminarán permanentemente tu cuenta, historial de películas, recomendaciones y transacciones. No hay forma de recuperar estos datos.
            </div>
          </div>

          {/* Contraseña */}
          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: '.72rem', color: '#6b7280', display: 'block', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '.04em' }}>
              Confirma tu contraseña para continuar
            </label>
            <PasswordInput
              value={deletePw}
              onChange={e => setDeletePw(e.target.value)}
              placeholder="Tu contraseña actual"
              autoComplete="off"
            />
          </div>

          {deleteError && (
            <div style={{ background: 'rgba(229,9,20,.08)', border: '1px solid rgba(229,9,20,.3)', color: '#f87171', padding: '8px 12px', borderRadius: 10, fontSize: '.82rem', marginBottom: 14 }}>
              ⚠ {deleteError}
            </div>
          )}

          <div style={{ display: 'flex', gap: 10 }}>
            <button
              type="button"
              onClick={() => setDeleteOpen(false)}
              disabled={deleteLoading}
              style={{ flex: 1, background: 'transparent', border: '1px solid #2a2a4a', color: '#9ca3af', padding: '10px', borderRadius: 30, fontWeight: 600, fontSize: '.86rem', cursor: 'pointer' }}
            >
              Cancelar
            </button>
            <button
              type="button"
              disabled={deleteLoading || !deletePw}
              onClick={async () => {
                setDeleteError('')
                setDeleteLoading(true)
                try {
                  await deleteAccount(deletePw)
                  // Logout completo en frontend
                  setDeleteOpen(false)
                  onClose()
                  logout()
                } catch (err) {
                  const msg = err?.response?.data?.error || 'Error al eliminar la cuenta'
                  setDeleteError(msg.toLowerCase().includes('incorrecta') ? 'Contraseña incorrecta' : msg)
                } finally {
                  setDeleteLoading(false)
                }
              }}
              style={{
                flex: 1,
                background: deleteLoading || !deletePw ? '#1f1f35' : 'linear-gradient(135deg,#b91c1c,#7f1d1d)',
                color: deleteLoading || !deletePw ? '#6b7280' : '#fff',
                border: 'none', padding: '10px', borderRadius: 30,
                fontWeight: 700, fontSize: '.86rem',
                cursor: deleteLoading || !deletePw ? 'not-allowed' : 'pointer',
              }}
            >
              {deleteLoading ? 'Eliminando...' : 'Sí, eliminar mi cuenta'}
            </button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
    </>
  )
}
