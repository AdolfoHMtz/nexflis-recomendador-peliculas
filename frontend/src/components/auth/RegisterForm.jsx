import { useState } from 'react'
import VisibilityIcon from '@mui/icons-material/Visibility'
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff'
import { useAuth } from '../../context/AuthContext'

export default function RegisterForm({ onSuccess, onGoLogin }) {
  const { register } = useAuth()
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [edad, setEdad] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!username || !password) { setError('Usuario y contraseña son obligatorios.'); return }
    if (!email || !email.includes('@')) { setError('Correo electrónico inválido.'); return }
    if (!edad) { setError('La edad es obligatoria.'); return }
    const edadNum = parseInt(edad, 10)
    if (isNaN(edadNum) || edadNum < 0 || edadNum > 120) { setError('Edad inválida (0–120).'); return }
    if (password !== confirm) { setError('Las contraseñas no coinciden.'); return }
    if (password.length < 6) { setError('La contraseña debe tener al menos 6 caracteres.'); return }
    setLoading(true); setError('')
    try {
      await register(username, password, edadNum, email)
      onSuccess?.()
    } catch (err) {
      setError(err?.response?.data?.error || 'El nombre de usuario ya está en uso.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-form">
      <h2 className="auth-title">Crear cuenta</h2>
      <p style={{ fontSize: '.9rem', color: '#9ca3af', marginBottom: 20 }}>
        Únete para guardar tu historial y recibir recomendaciones.
      </p>
      {error && <div className="auth-error">{error}</div>}
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Usuario <span style={{ fontSize: '.75rem', color: '#e50914' }}>*</span></label>
          <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="tu_usuario" autoComplete="username" />
        </div>
        <div className="form-group">
          <label>Correo electrónico <span style={{ fontSize: '.75rem', color: '#e50914' }}>*</span></label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="tu@correo.com" autoComplete="email" />
        </div>
        <div className="form-group">
          <label>Edad <span style={{ fontSize: '.75rem', color: '#e50914' }}>*</span></label>
          <input type="number" value={edad} onChange={(e) => setEdad(e.target.value)} placeholder="25" min="0" max="120" required />
          <div style={{ fontSize: '.75rem', color: '#666', marginTop: 4 }}>
            Si eres menor de 18 años, el contenido adulto será filtrado automáticamente.
          </div>
        </div>
        <div className="form-group">
          <label>Contraseña <span style={{ fontSize: '.75rem', color: '#e50914' }}>*</span></label>
          <div style={{ position: 'relative' }}>
            <input type={showPassword ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••  (mín. 6 caracteres)" autoComplete="new-password" style={{ paddingRight: 42 }} />
            <button type="button" onClick={() => setShowPassword(s => !s)} style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: '#6b7280', cursor: 'pointer', display: 'flex', alignItems: 'center', padding: 0 }}>
              {showPassword ? <VisibilityOffIcon sx={{ fontSize: '1.1rem' }} /> : <VisibilityIcon sx={{ fontSize: '1.1rem' }} />}
            </button>
          </div>
        </div>
        <div className="form-group">
          <label>Confirmar contraseña <span style={{ fontSize: '.75rem', color: '#e50914' }}>*</span></label>
          <div style={{ position: 'relative' }}>
            <input type={showConfirm ? 'text' : 'password'} value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="••••••" autoComplete="new-password" style={{ paddingRight: 42 }} />
            <button type="button" onClick={() => setShowConfirm(s => !s)} style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: '#6b7280', cursor: 'pointer', display: 'flex', alignItems: 'center', padding: 0 }}>
              {showConfirm ? <VisibilityOffIcon sx={{ fontSize: '1.1rem' }} /> : <VisibilityIcon sx={{ fontSize: '1.1rem' }} />}
            </button>
          </div>
        </div>
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? 'Registrando...' : 'Registrarse'}
        </button>
      </form>
      <p className="auth-switch">
        ¿Ya tienes cuenta?{' '}
        <button type="button" onClick={onGoLogin}>Iniciar sesión</button>
      </p>
    </div>
  )
}
