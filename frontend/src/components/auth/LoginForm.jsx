import { useState } from 'react'
import VisibilityIcon from '@mui/icons-material/Visibility'
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff'
import { useAuth } from '../../context/AuthContext'

export default function LoginForm({ onSuccess, onGoRegister }) {
  const { login } = useAuth()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!identifier || !password) { setError('Todos los campos son obligatorios.'); return }
    setLoading(true); setError('')
    try {
      await login(identifier, password)
      onSuccess?.()
    } catch {
      setError('Usuario, email o contraseña incorrectos.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-form">
      <h2 className="auth-title">Iniciar sesión</h2>
      <p style={{ fontSize: '.9rem', color: '#9ca3af', marginBottom: 20 }}>
        Accede a tus recomendaciones personalizadas.
      </p>
      {error && <div className="auth-error">{error}</div>}
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Usuario o email</label>
          <input
            type="text"
            value={identifier}
            onChange={e => setIdentifier(e.target.value)}
            placeholder="Tu usuario o correo"
            autoComplete="username"
          />
        </div>
        <div className="form-group">
          <label>Contraseña</label>
          <div style={{ position: 'relative' }}>
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Tu contraseña"
              autoComplete="current-password"
              style={{ paddingRight: 42 }}
            />
            <button
              type="button"
              onClick={() => setShowPassword(s => !s)}
              style={{
                position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
                background: 'none', border: 'none', color: '#6b7280', cursor: 'pointer',
                display: 'flex', alignItems: 'center', padding: 0,
              }}
            >
              {showPassword
                ? <VisibilityOffIcon sx={{ fontSize: '1.1rem' }} />
                : <VisibilityIcon sx={{ fontSize: '1.1rem' }} />
              }
            </button>
          </div>
        </div>
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? 'Entrando...' : 'Iniciar sesión'}
        </button>
      </form>
      <p className="auth-switch">
        ¿Sin cuenta?{' '}
        <button type="button" onClick={onGoRegister}>Registrarse</button>
      </p>
    </div>
  )
}
