import { useEffect, useState } from 'react'
import Dialog from '@mui/material/Dialog'
import DialogContent from '@mui/material/DialogContent'
import IconButton from '@mui/material/IconButton'
import Chip from '@mui/material/Chip'
import Tooltip from '@mui/material/Tooltip'
import CloseIcon from '@mui/icons-material/Close'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import StarIcon from '@mui/icons-material/Star'
import AccessTimeIcon from '@mui/icons-material/AccessTime'
import { getMovieDetail } from '../../api/movies'
import { useAuth } from '../../context/AuthContext'
import AgeBlockModal from './AgeBlockModal'
import CompleteProfileModal from './CompleteProfileModal'

const TMDB_IMG = 'https://image.tmdb.org/t/p/w500'

function ageLabel(edad) {
  if (edad >= 18) return '+18'
  if (edad >= 16) return '+16'
  if (edad >= 13) return '+13'
  if (edad >= 7)  return '+7'
  return 'G'
}

export default function InfoModal({ movie, onClose, onWatch }) {
  const { user } = useAuth()
  const [detail, setDetail] = useState(movie)
  const [showAgeBlock, setShowAgeBlock] = useState(false)
  const [showCompleteProfile, setShowCompleteProfile] = useState(false)
  const [pendingMovie, setPendingMovie] = useState(null)

  const handleWatch = (m) => {
    const clasificacion = m.clasificacion_edad || 0
    if (clasificacion > 0) {
      // Sin edad registrada → pedir completar perfil
      if (user?.edad == null) {
        setPendingMovie(m)
        setShowCompleteProfile(true)
        return
      }
      // Menor de edad para ese contenido → bloquear
      if (user.edad < clasificacion) {
        setShowAgeBlock(true)
        return
      }
    }
    onWatch?.(m)
  }

  const handleProfileComplete = (newEdad) => {
    setShowCompleteProfile(false)
    // Con la nueva edad, re-evaluar si puede ver la película
    const m = pendingMovie
    if (m) {
      const clasificacion = m.clasificacion_edad || 0
      if (newEdad < clasificacion) {
        setShowAgeBlock(true)
      } else {
        onWatch?.(m)
      }
    }
    setPendingMovie(null)
  }

  useEffect(() => {
    if (!movie) return
    setDetail(movie)
    const needsHydration = !movie.overview || !movie.cast_list?.length || !movie.director || !movie.clasificacion_edad
    if (movie.id && needsHydration) {
      getMovieDetail(movie.id).then((d) => setDetail((prev) => ({ ...prev, ...d }))).catch(() => {})
    }
  }, [movie])

  const m = detail || {}

  return (
    <>
    <AgeBlockModal
      open={showAgeBlock}
      onClose={() => setShowAgeBlock(false)}
      clasificacion={m.clasificacion_edad}
      titulo={m.title}
    />
    <CompleteProfileModal
      open={showCompleteProfile}
      onClose={() => { setShowCompleteProfile(false); setPendingMovie(null) }}
      onComplete={handleProfileComplete}
    />
    <Dialog
      open={!!movie}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          background: '#12121f',
          border: '1px solid #2a2a4a',
          borderRadius: '16px',
          color: '#e5e5e5',
          overflow: 'hidden',
        },
      }}
    >
      <DialogContent sx={{ p: 0 }}>
        <div style={{ display: 'flex', gap: 0 }}>
          {/* Poster */}
          <div style={{ flex: '0 0 220px', background: '#0d0d1a', alignSelf: 'flex-start' }}>
            {m.poster_path
              ? <img src={TMDB_IMG + m.poster_path} alt={m.title}
                  style={{ width: '220px', aspectRatio: '2/3', objectFit: 'cover', display: 'block' }} />
              : <div style={{ width: '220px', aspectRatio: '2/3', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#444' }}>
                  <i className="fa-solid fa-film fa-3x" />
                </div>}
          </div>

          {/* Content */}
          <div style={{ flex: 1, padding: '24px 24px 20px', overflow: 'auto', minWidth: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 }}>
              <h3 style={{ margin: 0, fontWeight: 700, fontSize: '1.25rem', lineHeight: 1.3, paddingRight: 32 }}>{m.title || 'Sin título'}</h3>
              <Tooltip title="Cerrar">
                <IconButton onClick={onClose} size="small" sx={{ color: '#9ca3af', mt: -0.5, mr: -1 }}>
                  <CloseIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </div>

            {/* Meta row */}
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8, marginBottom: 14 }}>
              {(m.genres_list || []).map((g) => (
                <Chip key={g} label={g} size="small"
                  sx={{ background: '#1e1e3a', color: '#c4b5fd', fontSize: '.7rem', height: 22, border: '1px solid #3a2a6a' }} />
              ))}
              {m.clasificacion_edad > 0 && (
                <Chip
                  label={ageLabel(m.clasificacion_edad)}
                  size="small"
                  sx={{
                    background: m.clasificacion_edad >= 18 ? 'rgba(220,38,38,.2)' : 'rgba(100,100,100,.2)',
                    color: m.clasificacion_edad >= 18 ? '#fca5a5' : '#9ca3af',
                    fontSize: '.7rem', height: 22,
                    border: `1px solid ${m.clasificacion_edad >= 18 ? 'rgba(220,38,38,.4)' : '#3a3a4a'}`,
                  }}
                />
              )}
              {m.release_date && (
                <span style={{ fontSize: '.78rem', color: '#9ca3af' }}>
                  {String(m.release_date).slice(0, 4)}
                </span>
              )}
              {m.runtime > 0 && (
                <span style={{ fontSize: '.78rem', color: '#9ca3af', display: 'flex', alignItems: 'center', gap: 3 }}>
                  <AccessTimeIcon sx={{ fontSize: '0.9rem' }} />{Math.round(m.runtime)} min
                </span>
              )}
              {m.vote_average > 0 && (
                <span style={{ fontSize: '.78rem', color: '#fbbf24', display: 'flex', alignItems: 'center', gap: 3 }}>
                  <StarIcon sx={{ fontSize: '0.9rem' }} />{m.vote_average}
                </span>
              )}
            </div>

            {/* Cast / Director */}
            {(m.cast_list?.length || m.director) && (
              <div style={{ fontSize: '.78rem', color: '#9ca3af', marginBottom: 14, lineHeight: 1.6 }}>
                {m.cast_list?.length > 0 && <span>{m.cast_list.slice(0, 4).join(', ')}</span>}
                {m.director && <span style={{ marginLeft: 6, color: '#6b7280' }}> · Dir. {m.director}</span>}
              </div>
            )}

            {/* Synopsis + keywords block */}
            <div style={{ background: '#0d0d1a', border: '1px solid #2a2a4a', borderRadius: 10, padding: '12px 14px', marginBottom: 18 }}>
              <div style={{ fontSize: '.65rem', color: '#6b7280', letterSpacing: '.8px', fontWeight: 700, marginBottom: 5 }}>SINOPSIS</div>
              <div style={{ fontSize: '.82rem', color: '#d1d5db', lineHeight: 1.55, maxHeight: 90, overflowY: 'auto' }}>
                {m.overview || 'Sinopsis no disponible'}
              </div>
              {m.keywords_list?.length > 0 && <>
                <div style={{ fontSize: '.65rem', color: '#6b7280', letterSpacing: '.8px', fontWeight: 700, marginTop: 10, marginBottom: 5 }}>KEYWORDS</div>
                <div style={{ fontSize: '.72rem', color: '#c4b5fd', lineHeight: 1.5 }}>
                  {m.keywords_list.slice(0, 8).join(' · ')}
                </div>
              </>}
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', gap: 10 }}>
              {onWatch && (
                <button onClick={() => handleWatch(m)} style={{
                  background: 'linear-gradient(135deg,#e50914,#b20710)', color: '#fff', border: 'none',
                  padding: '9px 20px', borderRadius: 30, fontWeight: 700, fontSize: '.85rem',
                  cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
                }}>
                  <PlayArrowIcon sx={{ fontSize: '1rem' }} /> Ver película
                </button>
              )}
              <button onClick={onClose} style={{
                background: 'transparent', border: '1px solid #4a4a6a', color: '#9ca3af',
                padding: '9px 20px', borderRadius: 30, fontSize: '.85rem', cursor: 'pointer',
              }}>
                Cerrar
              </button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
    </>
  )
}
