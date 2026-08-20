/**
 * The score, with the two reference markers from the dissertation.
 *
 * The markers are fetched from the API rather than written in as constants, so
 * that if the analysis is re-run and the figures move, the reference lines move
 * with them instead of quietly becoming wrong.
 */
export default function ScoreDisplay({ score, markers, delta, lostRules }) {
  if (!score) return <div className="score-card"><p>Scoring...</p></div>

  const rate = score.capture_rate
  // The axis must contain every reference marker. The best computed layout
  // sits at 100 (one giant zone captures everything), so when that marker is
  // present the axis runs the full range, which is itself the point: it shows
  // how far every practical layout sits from the metric's ceiling.
  const axisMax = Math.max(
    25,
    Math.ceil(rate * 1.15),
    ...markers.map((m) => Math.ceil(m.value)),
  )
  const pos = (v) => `${Math.min(100, (v / axisMax) * 100)}%`

  return (
    <div className="score-card">
      <div className="score-head">
        <div>
          <div className="score-big">{rate.toFixed(1)}<span className="pct">%</span></div>
          <div className="score-sub">of strong cross-sell support captured</div>
        </div>
        <div className="score-numbers">
          <div><strong>{score.rules_captured}</strong> of {score.total_strong_rules} rules</div>
          <div>{score.support_captured.toFixed(4)} of {score.total_strong_support} support</div>
          {delta != null && delta !== 0 && (
            <div className={delta > 0 ? 'delta-up' : 'delta-down'}>
              {delta > 0 ? '+' : ''}{delta} rules from last move
            </div>
          )}
        </div>
      </div>

      <div className="bar-wrap">
        <div className="bar">
          <div className="bar-fill" style={{ width: pos(rate) }} />
          {markers.map((m) => (
            <div key={m.label} className="marker" style={{ left: pos(m.value) }} title={m.label}>
              <div className="marker-line" />
              <div className="marker-label">
                {m.value.toFixed(1)}% {m.label}
              </div>
            </div>
          ))}
        </div>
        <div className="bar-axis"><span>0%</span><span>{axisMax}%</span></div>
      </div>

      <p className="ethics-summary">
        Of your {score.rules_captured} captured rules,{' '}
        <strong>{score.ethics.assists}</strong> {score.ethics.assists_label} and{' '}
        <strong>{score.ethics.creates}</strong> {score.ethics.creates_label}.
      </p>

      {lostRules && lostRules.length > 0 && (
        <div className="lost">
          <strong>That move lost {lostRules.length} rule{lostRules.length === 1 ? '' : 's'}:</strong>
          <ul>
            {lostRules.slice(0, 8).map((r) => (
              <li key={r.label}>
                {r.label} <span className="lost-meta">lift {r.lift.toFixed(2)}</span>
              </li>
            ))}
          </ul>
          {lostRules.length > 8 && <p className="lost-more">and {lostRules.length - 8} more</p>}
        </div>
      )}
    </div>
  )
}
