/**
 * DiffModal - Aparece cuando el usuario marca "No me gustó" antes de enviar.
 * Muestra la "Matriz de Algo Diferente": permite al usuario elegir qué dimensiones
 * quiere que sean diferentes en las recomendaciones.
 * El resultado se pasa junto con la reacción 'dislike' al motor.
 */
import Dialog from '@mui/material/Dialog'
import DialogContent from '@mui/material/DialogContent'
import IconButton from '@mui/material/IconButton'
import CloseIcon from '@mui/icons-material/Close'
import ExploreIcon from '@mui/icons-material/Explore'
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome'
import { useState } from 'react'

const DIFF_OPTIONS = [
  { key: 'diff_genero',    label: 'Géneros distintos',       icon: '🎭', desc: 'Busca otro estilo o género' },
  { key: 'diff_cast',      label: 'Otro reparto',            icon: '🎬', desc: 'Sin actores en común' },
  { key: 'diff_director',  label: 'Otro director',           icon: '🎥', desc: 'Diferente mano creativa' },
  { key: 'diff_semantica', label: 'Tono/temática diferente', icon: '🌈', desc: 'Sinopsis y palabras clave opuestas' },
  { key: 'diff_epoca',     label: 'Otra época',              icon: '📅', desc: 'Diferente año de lanzamiento' },
]

export default function DiffModal({ open, onClose, onConfirm, titulo }) {
  const [selected, setSelected] = useState({ diff_genero: true, diff_semantica: true, diff_cast: false, diff_director: false, diff_epoca: false })

  const toggle = (key) => setSelected((prev) => ({ ...prev, [key]: !prev[key] }))
  const anySelected = Object.values(selected).some(Boolean)

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="xs"
      fullWidth
      PaperProps={{
        sx: { background: '#12121f', border: '1px solid #2a2a4a', borderRadius: '16px', color: '#e5e5e5' },
      }}
    >
      <DialogContent sx={{ p: '24px' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <ExploreIcon sx={{ fontSize: '1.1rem', color: '#a78bfa' }} />
              <span style={{ fontWeight: 700, fontSize: '1rem' }}>Algo diferente a</span>
            </div>
            <div style={{ fontSize: '.82rem', color: '#a78bfa', fontStyle: 'italic' }}>{titulo}</div>
          </div>
          <IconButton onClick={onClose} size="small" sx={{ color: '#9ca3af', mt: -0.5, mr: -1 }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </div>

        <div style={{ fontSize: '.78rem', color: '#9ca3af', marginBottom: 14 }}>
          ¿En qué dimensiones quieres que sean <strong style={{ color: '#e5e5e5' }}>diferentes</strong> las recomendaciones?
        </div>

        {/* Options */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 20 }}>
          {DIFF_OPTIONS.map(({ key, label, icon, desc }) => {
            const active = selected[key]
            return (
              <button
                key={key}
                type="button"
                onClick={() => toggle(key)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  background: active ? 'rgba(167,139,250,.12)' : '#16162a',
                  border: `1px solid ${active ? 'rgba(167,139,250,.4)' : '#2a2a4a'}`,
                  borderRadius: 10, padding: '10px 14px', cursor: 'pointer',
                  transition: 'all .15s', textAlign: 'left',
                }}
              >
                <span style={{ fontSize: '1.2rem', lineHeight: 1 }}>{icon}</span>
                <div>
                  <div style={{ fontSize: '.82rem', fontWeight: active ? 700 : 500, color: active ? '#c4b5fd' : '#e5e5e5' }}>{label}</div>
                  <div style={{ fontSize: '.7rem', color: '#6b7280' }}>{desc}</div>
                </div>
                <div style={{
                  marginLeft: 'auto', width: 18, height: 18, borderRadius: '50%', flexShrink: 0,
                  background: active ? '#a78bfa' : 'transparent',
                  border: `2px solid ${active ? '#a78bfa' : '#3a3a5a'}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  {active && <span style={{ color: '#fff', fontSize: '.6rem', fontWeight: 700 }}>✓</span>}
                </div>
              </button>
            )
          })}
        </div>

        {/* Action */}
        <button
          onClick={() => anySelected && onConfirm(selected)}
          disabled={!anySelected}
          style={{
            width: '100%',
            background: anySelected ? 'linear-gradient(135deg,#7c3aed,#6d28d9)' : '#2a2a4a',
            color: anySelected ? '#fff' : '#6b7280',
            border: 'none', padding: '12px 24px', borderRadius: 30,
            fontWeight: 700, fontSize: '.88rem', cursor: anySelected ? 'pointer' : 'not-allowed',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            transition: 'all .2s',
          }}
        >
          <AutoAwesomeIcon sx={{ fontSize: '1rem' }} />
          Buscar algo diferente
        </button>
      </DialogContent>
    </Dialog>
  )
}
