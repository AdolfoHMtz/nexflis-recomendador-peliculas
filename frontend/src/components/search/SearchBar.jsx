import { useEffect, useRef, useState } from 'react'
import { search } from '../../api/movies'

const TMDB_IMG = 'https://image.tmdb.org/t/p/w92'

export default function SearchBar({ onSelectMovie }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [open, setOpen] = useState(false)
  const timer = useRef(null)
  const controller = useRef(null)
  const wrapRef = useRef(null)

  useEffect(() => {
    const handler = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleChange = (e) => {
    const q = e.target.value
    setQuery(q)
    clearTimeout(timer.current)
    if (q.trim().length < 2) { setOpen(false); return }
    timer.current = setTimeout(async () => {
      controller.current?.abort()
      controller.current = new AbortController()
      try {
        const data = await search(q)
        setResults(data)
        setOpen(true)
      } catch { /* aborted */ }
    }, 300)
  }

  const handleSelect = (movie) => {
    setQuery('')
    setOpen(false)
    onSelectMovie?.(movie)
  }

  return (
    <div className="search-wrapper" ref={wrapRef}>
      <i className="fa-solid fa-magnifying-glass search-icon" />
      <input
        type="text" className="search-input" placeholder="Buscar película..."
        autoComplete="off" value={query} onChange={handleChange}
      />
      {open && (
        <div className="search-dropdown">
          {results.length === 0 ? (
            <div className="p-3 text-secondary text-center small">No se encontraron resultados</div>
          ) : results.map((m) => (
            <div key={m.id} className="search-item" onClick={() => handleSelect(m)}>
              {m.poster_path
                ? <img src={TMDB_IMG + m.poster_path} className="search-thumb" alt="" />
                : <div className="search-thumb" style={{ background: '#1a1a2e', borderRadius: 4 }} />}
              <div>
                <div className="fw-bold small">{m.title}</div>
                <div className="text-secondary" style={{ fontSize: '0.7rem' }}>
                  {(m.genres_list || []).join(', ')} &middot; {m.runtime > 0 ? `${Math.round(m.runtime)} min` : 'Duración N/D'}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
