export default function ExplBar({ value, max }) {
  const pct = Math.min(100, Math.round((value / max) * 100))
  const cls = value < max * 0.33 ? 'bar-low' : value < max * 0.66 ? 'bar-mid' : 'bar-high'
  return (
    <div className="expl-bar-wrap">
      <div className="expl-bar-bg">
        <div className={`expl-bar-fill ${cls}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="expl-bar-pct">{(value * 100).toFixed(1)}%</span>
    </div>
  )
}
