import Tooltip from '@mui/material/Tooltip'

const TMDB_IMG = 'https://image.tmdb.org/t/p/w342'

function ageLabel(edad) {
  if (edad >= 18) return '+18'
  if (edad >= 16) return '+16'
  if (edad >= 13) return '+13'
  if (edad >= 7)  return '+7'
  return 'G'
}

export default function MovieCard({ movie, onClick, badge, progress }) {
  const poster = movie.poster_path ? TMDB_IMG + movie.poster_path : null
  const score = badge ?? (movie.score_final != null
    ? `${(movie.score_final * 100).toFixed(1)}%`
    : movie.vote_average > 0 ? `${Math.round(movie.vote_average * 10) / 10} ★` : null)

  return (
    <Tooltip title={movie.title} placement="top" arrow
      componentsProps={{ tooltip: { sx: { background: '#1e1e3a', fontSize: '.75rem', border: '1px solid #2a2a4a' } } }}>
      <div
        onClick={onClick}
        style={{
          flex: '0 0 auto', width: 150, cursor: onClick ? 'pointer' : 'default',
          transition: 'transform .25s', position: 'relative',
        }}
        onMouseEnter={(e) => { e.currentTarget.style.transform = 'scale(1.06)' }}
        onMouseLeave={(e) => { e.currentTarget.style.transform = 'scale(1)' }}
      >
        <div style={{ position: 'relative', borderRadius: 10, overflow: 'hidden', aspectRatio: '2/3', background: '#1a1a2e' }}>
          {poster
            ? <img src={poster} alt={movie.title}
                style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                onError={(e) => { e.target.style.display = 'none' }} />
            : <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#444' }}>
                <i className="fa-solid fa-film fa-2x" />
              </div>}

          {/* Score overlay */}
          {score && (
            <div style={{
              position: 'absolute', bottom: 6, right: 6,
              background: 'rgba(0,0,0,.75)', backdropFilter: 'blur(4px)',
              color: '#4ade80', fontSize: '.68rem', fontWeight: 700,
              padding: '2px 7px', borderRadius: 6, border: '1px solid rgba(74,222,128,.3)',
            }}>
              {score}
            </div>
          )}
          {/* Age rating overlay */}
          {movie.clasificacion_edad > 0 && (
            <div style={{
              position: 'absolute', top: 5, left: 5,
              background: movie.clasificacion_edad >= 18 ? 'rgba(220,38,38,.85)' : 'rgba(0,0,0,.7)',
              color: '#fff', fontSize: '.6rem', fontWeight: 700,
              padding: '1px 5px', borderRadius: 4, border: '1px solid rgba(255,255,255,.2)',
            }}>
              {ageLabel(movie.clasificacion_edad)}
            </div>
          )}
        </div>

        {/* Title */}
        <div style={{
          fontSize: '.75rem', fontWeight: 600, marginTop: 7, color: '#e5e5e5',
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {movie.title}
        </div>

        {/* Meta row: año · rating · runtime · clasificación */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginTop: 3, flexWrap: 'wrap' }}>
          {movie.release_date && (
            <span style={{ fontSize: '.62rem', color: '#9ca3af' }}>
              {String(movie.release_date).slice(0, 4)}
            </span>
          )}
          {movie.vote_average > 0 && (
            <span style={{ fontSize: '.62rem', color: '#fbbf24', fontWeight: 700 }}>
              · ★ {Math.round(movie.vote_average * 10) / 10}
            </span>
          )}
          {movie.runtime > 0 && (
            <span style={{ fontSize: '.62rem', color: '#6b7280' }}>
              · {Math.round(movie.runtime)}m
            </span>
          )}
          {movie.clasificacion_edad > 0 && (
            <span style={{
              fontSize: '.58rem', fontWeight: 700, padding: '0 4px', borderRadius: 3,
              background: movie.clasificacion_edad >= 18 ? 'rgba(220,38,38,.25)' : 'rgba(100,100,100,.25)',
              color: movie.clasificacion_edad >= 18 ? '#fca5a5' : '#9ca3af',
              border: `1px solid ${movie.clasificacion_edad >= 18 ? 'rgba(220,38,38,.4)' : '#3a3a4a'}`,
            }}>
              {ageLabel(movie.clasificacion_edad)}
            </span>
          )}
        </div>

        {/* Progress bar (historial) */}
        {progress != null && progress > 0 && (
          <div style={{ height: 3, background: '#333', borderRadius: 2, marginTop: 4 }}>
            <div style={{ height: '100%', background: '#e50914', borderRadius: 2, width: `${progress}%` }} />
          </div>
        )}

      </div>
    </Tooltip>
  )
}
