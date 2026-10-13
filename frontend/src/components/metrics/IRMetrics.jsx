import { useEffect, useState } from 'react'
import { getIRMetrics } from '../../api/movies'

export default function IRMetrics() {
  const [data, setData] = useState(null)
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)

  const load = async () => {
    if (loading) return
    setLoading(true)
    try {
      const d = await getIRMetrics()
      setData(d)
    } catch {
      setData(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (open && !data) load()
  }, [open])

  return (
    <div className="ir-metrics-panel mt-4">
      <button className="ir-metrics-toggle" onClick={() => setOpen((v) => !v)}>
        <i className="fa-solid fa-flask me-2" />
        Métricas IR del historial
        <i className={`fa-solid fa-chevron-${open ? 'up' : 'down'} ms-2`} />
      </button>

      {open && (
        <div className="ir-metrics-body mt-2">
          {loading && <div className="text-secondary small">Cargando métricas...</div>}
          {!loading && !data && <div className="text-secondary small">No hay datos disponibles.</div>}
          {!loading && data && (
            <>
              <div className="small text-secondary mb-2">
                Historial actual: <b>{data.n_historial}</b> película(s) —{' '}
                {(data.historial_titles || []).join(', ')}
              </div>

              {data.n_historial === 0 ? (
                <div className="text-secondary small">Aún no has registrado ninguna película.</div>
              ) : (
                <>
                  <h6 className="text-info mb-2"><i className="fa-solid fa-chart-bar me-1" /> Activación por técnica</h6>
                  <table className="expl-table mb-3">
                    <thead>
                      <tr><th>Técnica IR</th><th>Descripción</th><th className="text-end">Score prom.</th></tr>
                    </thead>
                    <tbody>
                      <TechRow icon="fa-diagram-venn" color="#93c5fd" name="Jaccard simple"
                        desc="Similitud de overviews/títulos" val={data.tecnicas.jaccard} />
                      <TechRow icon="fa-weight-hanging" color="#fcd34d" name="Jaccard ponderado IDF"
                        desc="Cast + géneros; pesos por rareza" val={data.tecnicas.jaccard_idf} />
                      <TechRow icon="fa-magnifying-glass" color="#f97316" name="BM25 / Intent"
                        desc="Similitud temática token-based" val={data.tecnicas.bm25} />
                      <TechRow icon="fa-circle-nodes" color="#4ade80" name="Semántica combinada"
                        desc="0.45·kw + 0.35·sinopsis + 0.20·título" val={data.tecnicas.semantica} />
                    </tbody>
                  </table>

                  {Object.keys(data.idf_terms || {}).length > 0 && (
                    <>
                      <h6 className="text-info mb-2"><i className="fa-solid fa-weight-hanging me-1" /> Top IDF por campo</h6>
                      <div className="d-flex flex-wrap gap-3">
                        {Object.entries(data.idf_terms).map(([field, terms]) => (
                          <div key={field} style={{ minWidth: 160 }}>
                            <div className="text-secondary small mb-1 text-capitalize">{field}</div>
                            {Object.entries(terms).slice(0, 5).map(([term, val]) => (
                              <div key={term} className="d-flex justify-content-between small">
                                <span>{term}</span>
                                <span className="text-secondary">{val.toFixed(2)}</span>
                              </div>
                            ))}
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </>
              )}
            </>
          )}
          <button className="btn-outline-secondary-custom mt-2 small" onClick={load} disabled={loading}>
            <i className="fa-solid fa-arrows-rotate me-1" /> Actualizar
          </button>
        </div>
      )}
    </div>
  )
}

function TechRow({ icon, color, name, desc, val }) {
  const pct = Math.min(100, Math.round(val * 100))
  return (
    <tr>
      <td><i className={`fa-solid ${icon} me-1`} style={{ color }} />{name}</td>
      <td className="text-secondary small">{desc}</td>
      <td className="text-end">
        <div className="expl-bar-wrap">
          <div className="expl-bar-bg"><div className="expl-bar-fill bar-high" style={{ width: `${pct}%` }} /></div>
          <span className="expl-bar-pct">{(val * 100).toFixed(1)}%</span>
        </div>
      </td>
    </tr>
  )
}
