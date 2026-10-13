import { useState } from 'react'
import Dialog from '@mui/material/Dialog'
import DialogContent from '@mui/material/DialogContent'
import IconButton from '@mui/material/IconButton'
import CloseIcon from '@mui/icons-material/Close'
import PersonIcon from '@mui/icons-material/Person'
import { updateProfile } from '../../api/auth'
import { useAuth } from '../../context/AuthContext'

/**
 * Modal que se muestra cuando el usuario no tiene edad registrada
 * e intenta ver contenido que requiere verificación de edad.
 * Permite completar el perfil con la edad sin salir del flujo.
 */
export default function CompleteProfileModal({ open, onClose, onComplete }) {
  const { setUser } = useAuth()
  const [edad, setEdad] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    const edadNum = parseInt(edad, 10)
    if (!edad || isNaN(edadNum) || edadNum < 1 || edadNum > 120) {
      setError('Introduce una edad válida (1-120)')
      return
    }
    setLoading(true)
    try {
      const updated = await updateProfile({ edad: edadNum })
      // Actualizar usuario en contexto con la nueva edad
      setUser((prev) => ({ ...prev, edad: updated.edad, needs_age: false }))
      onComplete?.(edadNum)
    } catch {
      setError('No se pudo guardar la edad. Inténtalo de nuevo.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="xs"
      fullWidth
      PaperProps={{
        sx: {
          background: '#12121f',
          border: '1px solid #2a2a4a',
          borderRadius: '16px',
          color: '#e5e5e5',
        },
      }}
    >
      <DialogContent sx={{ p: '28px' }}>
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 4 }}>
          <IconButton onClick={onClose} size="small" sx={{ color: '#9ca3af' }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </div>

        <div style={{ textAlign: 'center', marginBottom: 20 }}>
          <PersonIcon sx={{ fontSize: '2.8rem', color: '#60a5fa', mb: 1 }} />
          <div style={{ fontWeight: 700, fontSize: '1.05rem', marginBottom: 8 }}>
            Completa tu perfil
          </div>
          <div style={{ fontSize: '.85rem', color: '#9ca3af', lineHeight: 1.6 }}>
            Para acceder a este contenido necesitamos verificar tu edad.
            Tu perfil no tiene una edad registrada.
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: '.8rem', color: '#9ca3af', display: 'block', marginBottom: 6 }}>
              Tu edad
            </label>
            <input
              type="number"
              min="1"
              max="120"
              value={edad}
              onChange={(e) => setEdad(e.target.value)}
              placeholder="Ej: 25"
              style={{
                width: '100%', background: '#1a1a2e', border: '1px solid #3a3a5a',
                color: '#e5e5e5', borderRadius: 8, padding: '10px 14px',
                fontSize: '.9rem', outline: 'none', boxSizing: 'border-box',
              }}
              autoFocus
            />
            {error && (
              <div style={{ fontSize: '.78rem', color: '#f87171', marginTop: 6 }}>{error}</div>
            )}
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%', background: loading ? '#374151' : 'linear-gradient(135deg,#3b82f6,#1d4ed8)',
              color: '#fff', border: 'none', padding: '11px', borderRadius: 30,
              fontWeight: 700, fontSize: '.9rem', cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? 'Guardando...' : 'Guardar y continuar'}
          </button>
        </form>
      </DialogContent>
    </Dialog>
  )
}
