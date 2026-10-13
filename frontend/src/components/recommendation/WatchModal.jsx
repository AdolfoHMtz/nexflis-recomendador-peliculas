import { useState, useEffect } from 'react'
import DiffModal from './DiffModal'
import AgeBlockModal from './AgeBlockModal'
import CompleteProfileModal from './CompleteProfileModal'
import { useAuth } from '../../context/AuthContext'
import { getMovieDetail } from '../../api/movies'
import Dialog from '@mui/material/Dialog'
import DialogContent from '@mui/material/DialogContent'
import IconButton from '@mui/material/IconButton'
import Tooltip from '@mui/material/Tooltip'
import CloseIcon from '@mui/icons-material/Close'
import FavoriteIcon from '@mui/icons-material/Favorite'
import ThumbUpIcon from '@mui/icons-material/ThumbUp'
import ThumbDownIcon from '@mui/icons-material/ThumbDown'
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome'

const REACTIONS = [
  { value: 'double_like', label: 'Me encantó', Icon: FavoriteIcon, color: '#f472b6' },
  { value: 'like',        label: 'Me gustó',   Icon: ThumbUpIcon,  color: '#4ade80' },
  { value: 'dislike',     label: 'No me gustó', Icon: ThumbDownIcon, color: '#94a3b8' },
]

export default function WatchModal({ movie, onClose, onSubmit }) {
  const { user } = useAuth()
  const runtime = Math.round(movie?.runtime || 90)
  const [minutos, setMinutos] = useState(runtime)
  const [reaccion, setReaccion] = useState('like')
  const [loading, setLoading] = useState(false)
  const [showDiff, setShowDiff] = useState(false)
  const [showAgeBlock, setShowAgeBlock] = useState(false)
  const [showCompleteProfile, setShowCompleteProfile] = useState(false)
  const [hydratedMovie, setHydratedMovie] = useState(movie)

  // Hidratar datos de la película para obtener clasificacion_edad real
  useEffect(() => {
    if (!movie) return
    setHydratedMovie(movie)
    if (movie.id) {
      getMovieDetail(movie.id)
        .then((d) => setHydratedMovie((prev) => ({ ...prev, ...d })))
        .catch(() => {})
    }
  }, [movie])

  if (!movie) return null

  const clasificacion = hydratedMovie?.clasificacion_edad || 0

  // Verificar restricción de edad al intentar enviar
  const checkAge = () => {
    if (clasificacion > 0) {
      if (user?.edad == null) {
        setShowCompleteProfile(true)
        return false
      }
      if (user.edad < clasificacion) {
        setShowAgeBlock(true)
        return false
      }
    }
    return true
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (loading) return
    if (!checkAge()) return
    if (reaccion === 'dislike') {
      setShowDiff(true)
      return
    }
    await doSubmit({})
  }

  const doSubmit = async (diffOpts) => {
    setShowDiff(false)
    setLoading(true)
    try { await onSubmit(hydratedMovie, minutos, reaccion, diffOpts) }
    finally { setLoading(false) }
  }

  const handleProfileComplete = (newEdad) => {
    setShowCompleteProfile(false)
    if (newEdad < clasificacion) {
      setShowAgeBlock(true)
    }
    // Si puede ver → el usuario vuelve al modal y reintenta submit normalmente
  }

  const pct = runtime > 0 ? Math.round((minutos / runtime) * 100) : 0

  return (
    <>
    <AgeBlockModal
      open={showAgeBlock}
      onClose={() => setShowAgeBlock(false)}
      clasificacion={clasificacion}
      titulo={hydratedMovie.title}
    />
    <CompleteProfileModal
      open={showCompleteProfile}
      onClose={() => setShowCompleteProfile(false)}
      onComplete={handleProfileComplete}
    />
    <DiffModal
      open={showDiff}
      onClose={() => setShowDiff(false)}
      titulo={hydratedMovie.title}
      onConfirm={(diffOpts) => doSubmit(diffOpts)}
    />
    <Dialog
      open={!!movie}
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
      <DialogContent sx={{ p: '24px' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
          <div style={{ flex: 1, paddingRight: 8 }}>
            <div style={{ fontSize: '.7rem', color: '#6b7280', letterSpacing: '.8px', fontWeight: 700, marginBottom: 4 }}>REGISTRAR VISTA</div>
            <div style={{ fontWeight: 700, fontSize: '1rem', lineHeight: 1.3 }}>{hydratedMovie.title}</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 6 }}>
              {(hydratedMovie.genres_list || []).map((g) => (
                <span key={g} style={{ fontSize: '.65rem', color: '#c4b5fd', background: '#1e1e3a', border: '1px solid #3a2a6a', borderRadius: 4, padding: '1px 6px' }}>{g}</span>
              ))}
              {hydratedMovie.release_date && (
                <span style={{ fontSize: '.65rem', color: '#9ca3af' }}>{String(hydratedMovie.release_date).slice(0, 4)}</span>
              )}
              {clasificacion > 0 && (
                <span style={{ fontSize: '.65rem', fontWeight: 700, color: clasificacion >= 18 ? '#fca5a5' : '#9ca3af', background: clasificacion >= 18 ? 'rgba(220,38,38,.2)' : 'rgba(100,100,100,.2)', border: `1px solid ${clasificacion >= 18 ? 'rgba(220,38,38,.4)' : '#3a3a4a'}`, borderRadius: 4, padding: '1px 6px' }}>
                  {clasificacion >= 18 ? '+18' : clasificacion >= 16 ? '+16' : clasificacion >= 13 ? '+13' : clasificacion >= 7 ? '+7' : 'G'}
                </span>
              )}
            </div>
          </div>
          <Tooltip title="Cerrar">
            <IconButton onClick={onClose} size="small" sx={{ color: '#9ca3af', mt: -0.5, mr: -1 }}>
              <CloseIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </div>

        <form onSubmit={handleSubmit}>
          {/* Slider */}
          <div style={{ marginBottom: 22 }}>
            <div style={{ fontSize: '.78rem', color: '#9ca3af', marginBottom: 10 }}>¿Cuántos minutos viste?</div>
            <input
              type="range" min={0} max={runtime} value={minutos}
              onChange={(e) => setMinutos(Number(e.target.value))}
              style={{ width: '100%', accentColor: '#e50914', cursor: 'pointer' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '.75rem', color: '#6b7280', marginTop: 4 }}>
              <span>0 min</span>
              <span style={{ fontWeight: 700, color: '#e5e5e5', fontSize: '.9rem' }}>{minutos} min <span style={{ color: '#6b7280', fontSize: '.72rem' }}>({pct}%)</span></span>
              <span>{runtime} min</span>
            </div>
          </div>

          {/* Reactions */}
          <div style={{ marginBottom: 24 }}>
            <div style={{ fontSize: '.78rem', color: '#9ca3af', marginBottom: 10 }}>¿Cómo fue tu experiencia?</div>
            <div style={{ display: 'flex', gap: 8 }}>
              {REACTIONS.map(({ value, label, Icon, color }) => {
                const active = reaccion === value
                return (
                  <button
                    key={value} type="button"
                    onClick={() => setReaccion(value)}
                    style={{
                      flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
                      gap: 6, padding: '10px 8px', borderRadius: 12, cursor: 'pointer',
                      border: `2px solid ${active ? color : '#2a2a4a'}`,
                      background: active ? `${color}18` : '#16162a',
                      color: active ? color : '#9ca3af',
                      transition: 'all .18s', fontSize: '.72rem', fontWeight: active ? 700 : 400,
                    }}
                  >
                    <Icon sx={{ fontSize: '1.3rem', color: active ? color : '#6b7280' }} />
                    {label}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Submit */}
          <button type="submit" disabled={loading} style={{
            width: '100%', background: loading ? '#4a4a6a' : 'linear-gradient(135deg,#e50914,#b20710)',
            color: '#fff', border: 'none', padding: '13px 24px', borderRadius: 30,
            fontWeight: 700, fontSize: '.9rem', cursor: loading ? 'not-allowed' : 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            transition: 'all .2s',
          }}>
            {loading
              ? <><i className="fa-solid fa-spinner fa-spin" /> PROCESANDO...</>
              : <><AutoAwesomeIcon sx={{ fontSize: '1.1rem' }} /> OBTENER RECOMENDACIONES</>}
          </button>
        </form>
      </DialogContent>
    </Dialog>
    </>
  )
}
