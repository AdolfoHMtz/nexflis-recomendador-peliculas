import { useState } from 'react'
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome'
import ExploreIcon from '@mui/icons-material/Explore'
import MovieCard from './MovieCard'
import ExplModal from './ExplModal'
import InfoModal from './InfoModal'
import WatchModal from './WatchModal'

const TIPO_SEC_CONFIG = {
  te_encanto:  { color: '#ef4444', label: 'Porque te encantó' },
  te_gusto:    { color: '#22c55e', label: 'Porque te gustó' },
  no_te_gusto: { color: '#a78bfa', label: 'Algo diferente' },
}

export default function RecommendationSection({ recomendados, recomendados_sec, tipo_sec, ultima_peli, historial, onWatch }) {
  const [explMovie, setExplMovie] = useState(null)
  const [infoMovie, setInfoMovie] = useState(null)
  const [watchFromExpl, setWatchFromExpl] = useState(null)

  const handleWatchFromModal = (movie) => {
    setExplMovie(null)
    setInfoMovie(null)
    setTimeout(() => setWatchFromExpl(movie), 120)
  }

  const tipoConfig = TIPO_SEC_CONFIG[tipo_sec] || TIPO_SEC_CONFIG.te_gusto

  return (
    <>
      {/* Historial */}
      {historial?.length > 0 && (
        <SectionBlock
          icon="fa-clock-rotate-left"
          iconColor="#9ca3af"
          title="Volver a ver"
        >
          {historial.map((peli) => (
            <MovieCard key={peli.id} movie={peli} progress={peli.progreso}
              onClick={() => setInfoMovie(peli)} />
          ))}
        </SectionBlock>
      )}

      {/* Sección 1: Similares / Algo diferente */}
      {recomendados?.length > 0 && (
        <SectionBlock
          iconEl={<AutoAwesomeIcon sx={{ fontSize: '1rem', color: tipoConfig.color }} />}
          title={tipo_sec === 'no_te_gusto' ? 'Algo diferente' : `Similares · ${tipoConfig.label}`}
          subtitle={
            tipo_sec === 'no_te_gusto'
              ? 'Descubrimiento basado en lo que elegiste que quieres diferente.'
              : `10 películas similares a "${ultima_peli}" con su puntuación de relevancia.`
          }
        >
          {recomendados.map((peli) => (
            <MovieCard key={peli.id} movie={peli}
              badge={`${((peli.score_final || 0) * 100).toFixed(1)}%`}
              onClick={() => setExplMovie(peli)} />
          ))}
        </SectionBlock>
      )}

      {/* Sección 2: Fuera de dimensión (solo para like/double_like) */}
      {recomendados_sec?.length > 0 && (
        <SectionBlock
          iconEl={<ExploreIcon sx={{ fontSize: '1rem', color: '#a78bfa' }} />}
          title="Fuera de dimensión"
          subtitle={`Misma temática de "${ultima_peli}" pero fuera de su género principal — explora otra dimensión.`}
          accentColor="#a78bfa"
        >
          {recomendados_sec.map((peli) => (
            <MovieCard key={peli.id} movie={peli}
              badge={peli.score_final != null ? `${(peli.score_final * 100).toFixed(1)}%` : undefined}
              onClick={() => setExplMovie(peli)} />
          ))}
        </SectionBlock>
      )}

      {explMovie && <ExplModal movie={explMovie} onClose={() => setExplMovie(null)} onWatch={handleWatchFromModal} />}
      {infoMovie && <InfoModal movie={infoMovie} onClose={() => setInfoMovie(null)} onWatch={handleWatchFromModal} />}
      {watchFromExpl && (
        <WatchModal movie={watchFromExpl} onClose={() => setWatchFromExpl(null)}
          onSubmit={async (m, min, rea, diff) => { setWatchFromExpl(null); await onWatch?.(m, min, rea, diff) }} />
      )}
    </>
  )
}

function SectionBlock({ icon, iconColor, iconEl, title, subtitle, accentColor, children }) {
  return (
    <section style={{ marginBottom: 32 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
        {iconEl || (icon && <i className={`fa-solid ${icon}`} style={{ color: iconColor || '#e5e5e5', fontSize: '1rem' }} />)}
        <h4 style={{ margin: 0, fontWeight: 700, fontSize: '1.1rem', color: accentColor || '#e5e5e5' }}>{title}</h4>
      </div>
      {subtitle && <div style={{ fontSize: '.8rem', color: '#9ca3af', marginBottom: 12 }}>{subtitle}</div>}
      <div style={{ display: 'flex', gap: 14, overflowX: 'auto', paddingBottom: 10, scrollbarWidth: 'none', msOverflowStyle: 'none' }}>
        {children}
      </div>
    </section>
  )
}
