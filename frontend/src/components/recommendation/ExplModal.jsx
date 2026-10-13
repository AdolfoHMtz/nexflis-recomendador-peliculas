import { useEffect, useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import AgeBlockModal from './AgeBlockModal'
import Dialog from '@mui/material/Dialog'
import DialogContent from '@mui/material/DialogContent'
import IconButton from '@mui/material/IconButton'
import Chip from '@mui/material/Chip'

function ageLabel(edad) {
  if (edad >= 18) return '+18'
  if (edad >= 16) return '+16'
  if (edad >= 13) return '+13'
  if (edad >= 7)  return '+7'
  return 'G'
}
import Tooltip from '@mui/material/Tooltip'
import LinearProgress from '@mui/material/LinearProgress'
import CloseIcon from '@mui/icons-material/Close'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import StarIcon from '@mui/icons-material/Star'
import AccessTimeIcon from '@mui/icons-material/AccessTime'
import PsychologyIcon from '@mui/icons-material/Psychology'
import ScienceIcon from '@mui/icons-material/Science'
import FunctionsIcon from '@mui/icons-material/Functions'
import { getMovieDetail } from '../../api/movies'
import CompleteProfileModal from './CompleteProfileModal'

const TMDB_IMG = 'https://image.tmdb.org/t/p/w500'

const SCORE_ROWS = [
  { key: 'expl_cast',     label: 'Reparto',          weight: 0.15, color: '#22d3ee', detail: (p) => p.shared_cast?.length ? p.shared_cast.join(', ') : 'Ninguno en común', good: (p) => !!p.shared_cast?.length },
  { key: 'expl_saga',     label: 'Saga',             weight: 0.10, color: '#a78bfa', detail: (p) => p.same_saga ? `${p.saga_name} ✓` : `${p.saga_name || 'Sin saga'} ✗`,  good: (p) => p.same_saga },
  { key: 'expl_genres',   label: 'Géneros',          weight: 0.15, color: '#fbbf24', detail: (p) => p.shared_genres?.length ? p.shared_genres.join(', ') : 'Ninguno en común', good: (p) => !!p.shared_genres?.length },
  { key: 'expl_dir',      label: 'Director',         weight: 0.05, color: '#f87171', detail: (p) => p.same_director ? `${p.director} ✓` : `${p.director || 'N/D'} ✗`, good: (p) => p.same_director },
  { key: 'expl_semantic', label: 'Semántica',        weight: 0.20, color: '#60a5fa', detail: () => 'Sinopsis + título + keywords', good: () => true },
  { key: 'expl_intent',   label: 'Afinidad temática',weight: 0.10, color: '#34d399', detail: () => 'Franquicia / personaje / colección', good: () => true },
]
const BEHAV_ROWS = [
  { key: 'expl_reaccion', label: 'Reacción',    weight: 0.15, color: '#f472b6', detail: (p) => p.reaccion_label || 'Me gustó', good: (p) => p.val_reaccion > 0 },
  { key: 'expl_tiempo',   label: 'Tiempo visto',weight: 0.10, color: '#60a5fa', detail: (p) => `${Math.round((p.val_tiempo || 0) * 100)}% de la película`, good: () => true },
]
// Matriz "Algo diferente" (dislike) — 6 campos
const DIFF_ROWS = [
  { key: 'expl_genres',   label: 'Diff Géneros',   weight: 0.20, color: '#fbbf24', detail: (p) => p.shared_genres?.length ? `Comparte: ${p.shared_genres.join(', ')}` : 'Sin géneros en común ✓', good: (p) => !p.shared_genres?.length },
  { key: 'expl_cast',     label: 'Diff Reparto',   weight: 0.20, color: '#22d3ee', detail: (p) => p.shared_cast?.length ? `Comparte: ${p.shared_cast.join(', ')}` : 'Sin actores en común ✓', good: (p) => !p.shared_cast?.length },
  { key: 'expl_dir',      label: 'Diff Director',  weight: 0.20, color: '#f87171', detail: (p) => p.same_director ? `Mismo director ✗` : 'Director diferente ✓', good: (p) => !p.same_director },
  { key: 'expl_semantic', label: 'Diff Temática',  weight: 0.20, color: '#60a5fa', detail: () => 'Sinopsis + keywords diferentes', good: () => true },
  { key: 'expl_intent',   label: 'Diff Año',       weight: 0.10, color: '#34d399', detail: () => 'Diferencia de año de lanzamiento', good: () => true },
  { key: 'expl_tiempo',   label: 'Calificación',   weight: 0.10, color: '#a78bfa', detail: (p) => `${Math.round((p.val_tiempo || 0) * 10)} / 10`, good: (p) => (p.val_tiempo || 0) > 0.6 },
]

export default function ExplModal({ movie, onClose, onWatch }) {
  const { user } = useAuth()
  const [detail, setDetail] = useState(movie)
  const [showAgeBlock, setShowAgeBlock] = useState(false)
  const [showCompleteProfile, setShowCompleteProfile] = useState(false)
  const [pendingMovie, setPendingMovie] = useState(null)

  const handleWatch = (m) => {
    const clasificacion = m.clasificacion_edad || 0
    if (clasificacion > 0) {
      if (user?.edad == null) {
        setPendingMovie(m)
        setShowCompleteProfile(true)
        return
      }
      if (user.edad < clasificacion) {
        setShowAgeBlock(true)
        return
      }
    }
    onWatch?.(m)
  }

  const handleProfileComplete = (newEdad) => {
    setShowCompleteProfile(false)
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
    if (movie.id && (!movie.overview || !movie.keywords_list?.length)) {
      getMovieDetail(movie.id).then((d) => setDetail((prev) => ({ ...prev, ...d }))).catch(() => {})
    }
  }, [movie])

  const p = detail || {}
  const hasScore = p.score_final != null
  const isDiscover = p.reaccion_label === 'No me gustó' || p.diff_generos !== undefined

  return (
    <>
    <AgeBlockModal
      open={showAgeBlock}
      onClose={() => setShowAgeBlock(false)}
      clasificacion={p.clasificacion_edad}
      titulo={p.title}
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
          maxHeight: '92vh',
        },
      }}
    >
      <DialogContent sx={{ p: 0 }}>
        <div style={{ display: 'flex', minHeight: 0 }}>
          {/* Poster */}
          <div style={{ flex: '0 0 200px', background: '#0d0d1a', alignSelf: 'flex-start' }}>
            {p.poster_path
              ? <img src={TMDB_IMG + p.poster_path} alt={p.title}
                  style={{ width: '200px', aspectRatio: '2/3', objectFit: 'cover', display: 'block' }} />
              : <div style={{ width: '200px', aspectRatio: '2/3', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#444' }}>
                  <i className="fa-solid fa-film fa-3x" />
                </div>}
          </div>

          {/* Scrollable right panel */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '22px 22px 18px', minWidth: 0 }}>

            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
              <h3 style={{ margin: 0, fontWeight: 700, fontSize: '1.18rem', lineHeight: 1.3, paddingRight: 24 }}>{p.title}</h3>
              <Tooltip title="Cerrar">
                <IconButton onClick={onClose} size="small" sx={{ color: '#9ca3af', mt: -0.5, mr: -1 }}>
                  <CloseIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </div>

            {/* Meta */}
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 6, marginBottom: 14 }}>
              {(p.genres_list || []).map((g) => (
                <Chip key={g} label={g} size="small"
                  sx={{ background: '#1e1e3a', color: '#c4b5fd', fontSize: '.68rem', height: 20, border: '1px solid #3a2a6a' }} />
              ))}
              {p.clasificacion_edad > 0 && (
                <Chip
                  label={ageLabel(p.clasificacion_edad)}
                  size="small"
                  sx={{
                    background: p.clasificacion_edad >= 18 ? 'rgba(220,38,38,.2)' : 'rgba(100,100,100,.2)',
                    color: p.clasificacion_edad >= 18 ? '#fca5a5' : '#9ca3af',
                    fontSize: '.68rem', height: 20,
                    border: `1px solid ${p.clasificacion_edad >= 18 ? 'rgba(220,38,38,.4)' : '#3a3a4a'}`,
                  }}
                />
              )}
              {p.release_date && (
                <span style={{ fontSize: '.75rem', color: '#9ca3af' }}>
                  {String(p.release_date).slice(0, 4)}
                </span>
              )}
              {p.runtime > 0 && (
                <span style={{ fontSize: '.75rem', color: '#9ca3af', display: 'flex', alignItems: 'center', gap: 3 }}>
                  <AccessTimeIcon sx={{ fontSize: '.85rem' }} />{Math.round(p.runtime)} min
                </span>
              )}
              {p.vote_average > 0 && (
                <span style={{ fontSize: '.75rem', color: '#fbbf24', display: 'flex', alignItems: 'center', gap: 3 }}>
                  <StarIcon sx={{ fontSize: '.85rem' }} />{p.vote_average}
                </span>
              )}
            </div>

            {/* Synopsis block */}
            <div style={{ background: '#0d0d1a', border: '1px solid #2a2a4a', borderRadius: 10, padding: '10px 13px', marginBottom: 16 }}>
              <div style={LABEL_STYLE}>SINOPSIS</div>
              <div style={{ fontSize: '.8rem', color: '#d1d5db', lineHeight: 1.55, maxHeight: 80, overflowY: 'auto' }}>
                {p.overview || 'Sinopsis no disponible'}
              </div>
              {p.keywords_list?.length > 0 && <>
                <div style={{ ...LABEL_STYLE, marginTop: 9 }}>KEYWORDS</div>
                <div style={{ fontSize: '.7rem', color: '#c4b5fd', lineHeight: 1.5 }}>
                  {p.keywords_list.slice(0, 8).join(' · ')}
                </div>
              </>}
            </div>

            {/* Score matrix */}
            {hasScore && (
              <>
                <SectionHeader
                  icon={<PsychologyIcon sx={{ fontSize: '1rem', color: isDiscover ? '#a78bfa' : '#22d3ee' }} />}
                  title={isDiscover ? 'Matriz Algo Diferente (6 variables)' : 'Matriz de relevancia (8 variables = 100%)'}
                />

                <div style={{ marginBottom: 4 }}>
                  {isDiscover ? (
                    DIFF_ROWS.map((row) => (
                      <ScoreRow key={row.key} row={row} peli={p} />
                    ))
                  ) : (
                    <>
                      <GroupCaption label="CONTENIDO  ·  75%" />
                      {SCORE_ROWS.map((row) => (
                        <ScoreRow key={row.key} row={row} peli={p} />
                      ))}
                      <GroupCaption label="COMPORTAMIENTO DEL USUARIO  ·  25%" />
                      {BEHAV_ROWS.map((row) => (
                        <ScoreRow key={row.key} row={row} peli={p} />
                      ))}
                    </>
                  )}
                </div>

                {/* Score final */}
                <div style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '10px 14px', background: '#0d0d1a', border: '1px solid #2a2a4a',
                  borderRadius: 10, margin: '14px 0 14px',
                }}>
                  <span style={{ fontWeight: 700, fontSize: '.85rem', letterSpacing: '.5px' }}>SCORE FINAL</span>
                  <span style={{
                    background: '#14532d', color: '#4ade80', fontWeight: 700,
                    fontSize: '1.1rem', padding: '4px 14px', borderRadius: 8,
                  }}>
                    {(p.score_final * 100).toFixed(1)}%
                  </span>
                </div>

                {/* IR Techniques */}
                <SectionHeader icon={<ScienceIcon sx={{ fontSize: '1rem', color: '#60a5fa' }} />} title="Técnicas de Recuperación de Información" />
                <div style={{ background: 'linear-gradient(135deg,#0d1117,#12182a)', border: '1px solid #1e2d4a', borderRadius: 10, padding: '10px 12px', marginBottom: 14 }}>
                  <IRTechRow color="#93c5fd" name="VSM" desc="Similitud coseno sobre géneros, keywords y sinopsis" val={(p.expl_semantic * 100).toFixed(1)} />
                  <IRTechRow color="#fcd34d" name="TF-IDF" desc="Pondera términos raros; aplicado en Jaccard ponderado" val={((( p.expl_cast || 0) + (p.expl_genres || 0)) * 100).toFixed(1)} />
                  <IRTechRow color="#4ade80" name="Jaccard ponderado" desc="Reparto y géneros con pesos IDF del historial" val={((( p.expl_cast || 0) + (p.expl_genres || 0)) * 100).toFixed(1)} />
                  <IRTechRow color="#f97316" name="BM25" desc="Ranking probabilístico en búsqueda de candidatas" val="—" na />
                  <IRTechRow color="#a78bfa" name="Modelo Booleano" desc="AND/OR/NOT sobre géneros, keywords, actores" val="—" na />
                  <IRTechRow color="#34d399" name="Grafo de transiciones" desc="Distancia entre géneros (0=mismo, 0.3=directo…)" val="—" na />
                </div>

                {/* Heuristic formula */}
                <SectionHeader icon={<FunctionsIcon sx={{ fontSize: '1rem', color: '#a78bfa' }} />} title="Función de evaluación" />
                <div style={{
                  background: '#0d0d1a', border: '1px solid #2a2a4a', borderRadius: 10,
                  padding: '12px 14px', marginBottom: 16, fontFamily: 'monospace', fontSize: '.75rem', lineHeight: 2,
                }}>
                  {isDiscover ? (
                    <>
                      <div>
                        <span style={{ color: '#a78bfa' }}>f(x)</span> ={' '}
                        <Coef>0.20</Coef>·<em>ΔGéneros</em> + <Coef>0.20</Coef>·<em>ΔReparto</em> + <Coef>0.20</Coef>·<em>ΔDirector</em> +{' '}
                        <Coef>0.20</Coef>·<em>ΔTemática</em> + <Coef>0.10</Coef>·<em>ΔAño</em> + <Coef>0.10</Coef>·<em>Calidad</em>
                      </div>
                      <div style={{ borderTop: '1px solid #2a2a4a', paddingTop: 6, marginTop: 4, fontSize: '.68rem', color: '#6b7280', lineHeight: 1.7 }}>
                        Δ = 1 − similitud (0 = igual, 1 = totalmente diferente)<br />
                        Dimensiones seleccionadas en DiffModal reciben peso ×2<br />
                        <span style={{ color: '#60a5fa' }}>ΔTemática</span> = 0.6·kw_diff + 0.4·sinopsis_diff
                      </div>
                    </>
                  ) : (
                    <>
                      <div>
                        <span style={{ color: '#4ade80' }}>f(x)</span> ={' '}
                        <Coef>0.15</Coef>·<em>Reparto</em> + <Coef>0.10</Coef>·<em>Saga</em> + <Coef>0.15</Coef>·<em>Género</em> +{' '}
                        <Coef>0.05</Coef>·<em>Director</em> + <Coef>0.20</Coef>·<em>Semántica</em> +{' '}
                        <Coef>0.10</Coef>·<em>Afinidad</em> + <Coef>0.15</Coef>·<em>Reacción</em> + <Coef>0.10</Coef>·<em>Tiempo</em>
                      </div>
                      <div style={{ borderTop: '1px solid #2a2a4a', paddingTop: 6, marginTop: 4, fontSize: '.68rem', color: '#6b7280', lineHeight: 1.7 }}>
                        <span style={{ color: '#93c5fd' }}>Reparto/Género</span> = Jaccard ponderado IDF &nbsp;
                        <span style={{ color: '#c4b5fd' }}>Saga</span> = &#123;1,0&#125; &nbsp;
                        <span style={{ color: '#fca5a5' }}>Director</span> = &#123;1,0&#125;
                        <br />
                        <span style={{ color: '#fcd34d' }}>Semántica</span> = 0.45·kw + 0.35·sinopsis + 0.20·título &nbsp;
                        <span style={{ color: '#34d399' }}>Afinidad</span> = sim franquicia/colección
                        <br />
                        Agregación historial = 0.65·mejor + 0.35·segundo (robust top-2)
                      </div>
                    </>
                  )}
                </div>
              </>
            )}

            {/* Actions */}
            <div style={{ display: 'flex', gap: 10 }}>
              {onWatch && (
                <button onClick={() => handleWatch(p)} style={{
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

/* ---- Sub-components ---- */

const LABEL_STYLE = { fontSize: '.63rem', color: '#6b7280', letterSpacing: '.8px', fontWeight: 700, marginBottom: 5 }

function SectionHeader({ icon, title }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 10, marginTop: 2 }}>
      {icon}
      <span style={{ fontSize: '.78rem', fontWeight: 700, color: '#e2e8f0', letterSpacing: '.3px' }}>{title}</span>
    </div>
  )
}

function GroupCaption({ label }) {
  return (
    <div style={{ fontSize: '.62rem', color: '#6b7280', letterSpacing: '1px', fontWeight: 700, padding: '8px 0 5px' }}>
      {label}
    </div>
  )
}

function ScoreRow({ row, peli }) {
  const value = peli[row.key] || 0
  const pct = Math.min(100, Math.round((value / row.weight) * 100))
  const detail = row.detail(peli)
  const good = row.good(peli)

  return (
    <div style={{
      display: 'grid', gridTemplateColumns: '110px 38px 1fr 90px',
      alignItems: 'center', gap: 8, padding: '5px 0',
      borderBottom: '1px solid #1a1a2e',
    }}>
      <div style={{ fontSize: '.8rem', fontWeight: 600, color: '#e2e8f0', display: 'flex', alignItems: 'center', gap: 5 }}>
        <span style={{ width: 8, height: 8, borderRadius: '50%', background: row.color, display: 'inline-block', flexShrink: 0 }} />
        {row.label}
      </div>
      <div style={{ fontSize: '.7rem', color: '#6b7280', textAlign: 'center' }}>{Math.round(row.weight * 100)}%</div>
      <div style={{ fontSize: '.72rem', color: good ? '#4ade80' : '#6b7280', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {detail}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
        <LinearProgress
          variant="determinate" value={pct}
          sx={{
            flex: 1, height: 5, borderRadius: 4, background: '#1e1e2e',
            '& .MuiLinearProgress-bar': {
              background: pct < 33 ? 'linear-gradient(90deg,#f87171,#fb923c)'
                : pct < 66 ? 'linear-gradient(90deg,#fbbf24,#4ade80)'
                : 'linear-gradient(90deg,#4ade80,#22d3ee)',
              borderRadius: 4,
            },
          }}
        />
        <span style={{ fontSize: '.7rem', fontWeight: 700, color: '#4ade80', minWidth: 36, textAlign: 'right' }}>
          {(value * 100).toFixed(1)}%
        </span>
      </div>
    </div>
  )
}

function IRTechRow({ color, name, desc, val, na }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 0', borderBottom: '1px solid #1a2035', fontSize: '.72rem' }}>
      <span style={{ width: 8, height: 8, borderRadius: '50%', background: color, flexShrink: 0 }} />
      <span style={{ fontWeight: 700, color: '#e2e8f0', minWidth: 120 }}>{name}</span>
      <span style={{ color: '#6b7280', flex: 1 }}>{desc}</span>
      <span style={{ fontWeight: 700, color: na ? '#4b5563' : '#4ade80', minWidth: 36, textAlign: 'right' }}>{val}</span>
    </div>
  )
}

function Coef({ children }) {
  return <span style={{ color: '#60a5fa' }}>{children}</span>
}
