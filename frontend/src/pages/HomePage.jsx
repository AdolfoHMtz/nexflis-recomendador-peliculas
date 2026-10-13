import { useEffect, useRef, useState } from 'react'
import HeroSearch from '../components/search/HeroSearch'
import RecommendationSection from '../components/recommendation/RecommendationSection'
import WatchModal from '../components/recommendation/WatchModal'
import InfoModal from '../components/recommendation/InfoModal'
import MovieCard from '../components/recommendation/MovieCard'
import { recomendar, getHome, getUserHistorial, getUltimaConsulta } from '../api/movies'
import { useReco } from '../context/RecoContext'
import { useAuth } from '../context/AuthContext'

export default function HomePage() {
  const heroRef = useRef(null)
  const { registerHandler } = useReco()
  const { user } = useAuth()
  const [watchMovie, setWatchMovie] = useState(null)
  const [infoMovie, setInfoMovie] = useState(null)
  const [recoData, setRecoData] = useState(null)
  const [homeData, setHomeData] = useState({ top_10: [], historial: [], ultima_peli: null })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    // Al cambiar de usuario (login, logout, cambio de cuenta), limpiar estado previo
    setRecoData(null)
    setHomeData({ top_10: [], historial: [], ultima_peli: null })

    if (!user) return  // sin sesión: no cargar historial

    getHome().then(setHomeData).catch(() => {})
    getUserHistorial()
      .then((hist) => { if (hist?.length) setHomeData((prev) => ({ ...prev, historial: hist })) })
      .catch(() => {})
    // Restaurar última consulta persistida en BD (no usamos su historial, ese viene de getUserHistorial)
    getUltimaConsulta()
      .then((consulta) => {
        if (consulta?.recomendados?.length) {
          const { historial: _ignored, ...recoSinHistorial } = consulta
          setRecoData(recoSinHistorial)
        }
      })
      .catch(() => {})
  }, [user?.id])  // depende del ID, no del objeto (evita loops)

  // Registra handleWatch para que el Navbar pueda disparar recomendaciones
  useEffect(() => {
    registerHandler(handleWatch)
  })

  const handleWatch = async (movie, minutos, reaccion, diffOpts = {}) => {
    setLoading(true); setError('')
    try {
      const data = await recomendar(movie.id, movie.title, minutos, reaccion, diffOpts)
      setRecoData(data)
      // Refresca historial completo desde BD
      getUserHistorial()
        .then((hist) => { if (hist?.length) setHomeData((prev) => ({ ...prev, historial: hist })) })
        .catch(() => {})
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch {
      setError('No se pudo obtener recomendaciones. Intenta de nuevo.')
    } finally {
      setLoading(false)
    }
  }

  // historial siempre desde BD (homeData), nunca del recoData (que solo tiene sesión de 5)
  const historialVisible = homeData.historial

  return (
    <div className="container-fluid px-4 px-md-5 pb-5">
      <HeroSearch ref={heroRef} onSelectMovie={(m) => setInfoMovie(m)} />

      {error && <div className="alert-error mb-3">{error}</div>}
      {loading && (
        <div className="text-center py-5">
          <i className="fa-solid fa-spinner fa-spin fa-2x text-info" />
          <div className="text-secondary mt-2">Calculando recomendaciones...</div>
        </div>
      )}

      {recoData && !loading && (
        <RecommendationSection
          recomendados={recoData.recomendados}
          recomendados_sec={recoData.recomendados_sec}
          tipo_sec={recoData.tipo_sec}
          ultima_peli={recoData.ultima_peli}
          historial={historialVisible}
          onWatch={handleWatch}
        />
      )}

      {/* Historial inicial (antes de primera recomendación) */}
      {!recoData && !loading && historialVisible.length > 0 && (
        <section style={{ marginBottom: 32 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
            <i className="fa-solid fa-clock-rotate-left" style={{ color: '#9ca3af' }} />
            <h4 style={{ margin: 0, fontWeight: 700, fontSize: '1.1rem' }}>Volver a ver</h4>
          </div>
          <div style={{ display: 'flex', gap: 14, overflowX: 'auto', paddingBottom: 10, scrollbarWidth: 'none' }}>
            {historialVisible.map((peli) => (
              <MovieCard key={peli.id} movie={peli} progress={peli.progreso}
                onClick={() => setWatchMovie(peli)} />
            ))}
          </div>
        </section>
      )}

      {/* Top 10 Popular */}
      {homeData.top_10.length > 0 && (
        <section style={{ marginBottom: 32 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
            <i className="fa-solid fa-fire" style={{ color: '#fbbf24' }} />
            <h4 style={{ margin: 0, fontWeight: 700, fontSize: '1.1rem' }}>Top 10 Popular</h4>
          </div>
          <div style={{ display: 'flex', gap: 14, overflowX: 'auto', paddingBottom: 10, scrollbarWidth: 'none' }}>
            {homeData.top_10.map((peli) => (
              <MovieCard key={peli.id} movie={peli}
                badge={`${Math.round((peli.vote_average || 0) * 10) / 10} ★`}
                onClick={() => setInfoMovie(peli)} />
            ))}
          </div>
        </section>
      )}

      {watchMovie && (
        <WatchModal
          movie={watchMovie}
          onClose={() => setWatchMovie(null)}
          onSubmit={async (m, min, rea, diff) => { setWatchMovie(null); await handleWatch(m, min, rea, diff) }}
        />
      )}
      {infoMovie && (
        <InfoModal
          movie={infoMovie}
          onClose={() => setInfoMovie(null)}
          onWatch={(m) => { setInfoMovie(null); setWatchMovie(m) }}
        />
      )}
    </div>
  )
}
