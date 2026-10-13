import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react'
import { getHeroOptions, heroSearch } from '../../api/movies'
import MovieCard from '../recommendation/MovieCard'

const DIMENSIONS = [
  { key: 'genre', label: 'Géneros', bucket: 'genres' },
  { key: 'keyword', label: 'Keywords', bucket: 'keywords' },
  { key: 'actor', label: 'Actores', bucket: 'actors' },
  { key: 'director', label: 'Directores', bucket: 'directors' },
  { key: 'collection', label: 'Sagas', bucket: 'collections' },
]
const LOGIC_MODES = ['and', 'or', 'not']

const EMPTY_SELECTED = { genres: [], keywords: [], actors: [], directors: [], collections: [] }

const HeroSearch = forwardRef(function HeroSearch({ onSelectMovie }, ref) {
  const [activeDim, setActiveDim] = useState('genre')
  const [logicMode, setLogicMode] = useState('and')
  const [selected, setSelected] = useState(EMPTY_SELECTED)
  const [facetQuery, setFacetQuery] = useState('')
  const [options, setOptions] = useState([])
  const [showOptions, setShowOptions] = useState(false)
  const [results, setResults] = useState(null)
  const [fallback, setFallback] = useState('')
  const [loading, setLoading] = useState(false)
  const timer = useRef(null)
  const optRef = useRef(null)

  useImperativeHandle(ref, () => ({
    reset() {
      setSelected(EMPTY_SELECTED)
      setFacetQuery('')
      setOptions([])
      setShowOptions(false)
      setResults(null)
      setFallback('')
      setLogicMode('and')
      setActiveDim('genre')
    },
  }))

  useEffect(() => {
    const handler = (e) => {
      if (optRef.current && !optRef.current.contains(e.target)) setShowOptions(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const fetchOptions = async (dim, q) => {
    try {
      const data = await getHeroOptions(dim, q)
      setOptions(data)
      setShowOptions(true)
    } catch { setShowOptions(false) }
  }

  const handleFacetInput = (e) => {
    const q = e.target.value
    setFacetQuery(q)
    clearTimeout(timer.current)
    timer.current = setTimeout(() => fetchOptions(activeDim, q), 300)
  }

  const handleFacetFocus = () => fetchOptions(activeDim, facetQuery)

  const addOption = (opt) => {
    const dim = DIMENSIONS.find((d) => d.key === activeDim)
    if (!dim) return
    const bucket = dim.bucket
    if (selected[bucket].some((x) => Number(x.id) === Number(opt.id))) return
    setSelected((prev) => ({ ...prev, [bucket]: [...prev[bucket], { id: opt.id, name: opt.name }] }))
    setFacetQuery('')
    setShowOptions(false)
  }

  const removeChip = (bucket, id) => {
    setSelected((prev) => ({ ...prev, [bucket]: prev[bucket].filter((x) => Number(x.id) !== Number(id)) }))
  }

  const allChips = DIMENSIONS.flatMap((d) =>
    selected[d.bucket].map((it) => ({ bucket: d.bucket, ...it }))
  )

  const runSearch = async () => {
    if (loading) return
    setLoading(true)
    try {
      const payload = await heroSearch(selected, logicMode)
      setFallback(payload.fallback ? 'Sin coincidencias exactas; mostramos opciones cercanas.' : 'Coincidencia exacta.')
      setResults(payload.results || [])
    } catch {
      setFallback('No se pudo completar la búsqueda.')
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const activeDimObj = DIMENSIONS.find((d) => d.key === activeDim)
  const placeholder = `Buscar por ${activeDimObj?.label || ''}...`

  return (
    <section className="hero-panel mt-3 mb-4">
      <div className="d-flex justify-content-between align-items-start gap-2">
        <div>
          <div className="hero-title">¿Qué quieres ver hoy?</div>
          <div className="hero-subtitle">Selecciona dimensiones y modo lógico para combinar filtros.</div>
        </div>
        <details className="query-help">
          <summary title="Ayuda de búsqueda">
            <i className="fa-solid fa-circle-question me-1" /> Ayuda
          </summary>
          <div className="query-help-box mt-2">
            <div className="query-help-title"><i className="fa-solid fa-circle-info me-1" /> Modos de combinación</div>
            <ul className="query-help-list mb-0">
              <li><strong>AND</strong>: exige que se cumplan todas las dimensiones.</li>
              <li><strong>OR</strong>: une resultados de cualquiera de las dimensiones.</li>
              <li><strong>NOT</strong>: excluye de populares lo que coincida con tus filtros.</li>
            </ul>
          </div>
        </details>
      </div>

      {/* Dimension buttons */}
      <div className="d-flex flex-wrap gap-2 mt-3">
        {DIMENSIONS.map((d) => (
          <button key={d.key}
            className={`hero-dim-btn${activeDim === d.key ? ' active' : ''}`}
            onClick={() => { setActiveDim(d.key); setFacetQuery(''); setShowOptions(false) }}
          >{d.label}</button>
        ))}
      </div>

      {/* Logic mode */}
      <div className="d-flex gap-2 mt-2">
        {LOGIC_MODES.map((m) => (
          <button key={m}
            className={`hero-logic-btn${logicMode === m ? ' active' : ''}`}
            onClick={() => setLogicMode(m)}
          >{m.toUpperCase()}</button>
        ))}
      </div>

      {/* Facet input */}
      <div className="facet-input-wrapper mt-3" ref={optRef}>
        <input
          type="text" className="facet-input" placeholder={placeholder}
          value={facetQuery} onChange={handleFacetInput} onFocus={handleFacetFocus}
        />
        {showOptions && (
          <div className="search-dropdown">
            {options.length === 0
              ? <div className="p-3 text-secondary text-center small">Sin opciones</div>
              : options.map((o) => (
                <div key={o.id} className="search-item" onClick={() => addOption(o)}>
                  <div><div className="fw-bold small">{o.name}</div></div>
                </div>
              ))}
          </div>
        )}
      </div>

      {/* Selected chips */}
      <div className="hero-chips mt-2">
        {allChips.map((chip) => (
          <span key={`${chip.bucket}-${chip.id}`} className="hero-chip">
            <b>{chip.bucket.slice(0, -1)}</b> {chip.name}
            <button type="button" onClick={() => removeChip(chip.bucket, chip.id)}>
              <i className="fa-solid fa-xmark" />
            </button>
          </span>
        ))}
      </div>

      {/* Summary */}
      <div className="hero-summary mt-2">
        Deseas buscar algo con:{' '}
        {allChips.length === 0
          ? <span className="text-secondary">(aún sin filtros)</span>
          : <span style={{ color: '#c4b5fd' }}>{allChips.map((c) => c.name).join(', ')}</span>}
        {' '}· modo <b>{logicMode.toUpperCase()}</b>
      </div>

      <button className="btn-primary mt-3" onClick={runSearch} disabled={loading}>
        {loading
          ? <><i className="fa-solid fa-spinner fa-spin me-1" /> Buscando...</>
          : <><i className="fa-solid fa-sparkles me-1" /> Buscar</>}
      </button>

      {/* Results */}
      {results !== null && (
        <div className="mt-4">
          {fallback && <div className="text-secondary small mb-2">{fallback}</div>}
          {results.length === 0
            ? <div className="text-secondary small">No encontramos resultados con esos filtros.</div>
            : <div className="movie-grid">
              {results.map((m) => (
                <MovieCard key={m.id} movie={m} onClick={() => {
                  setSelected(EMPTY_SELECTED)
                  setFacetQuery('')
                  setOptions([])
                  setShowOptions(false)
                  setResults(null)
                  setFallback('')
                  onSelectMovie?.(m)
                }} />
              ))}
            </div>}
        </div>
      )}
    </section>
  )
})

export default HeroSearch
