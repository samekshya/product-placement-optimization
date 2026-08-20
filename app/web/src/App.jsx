import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { DndContext, DragOverlay, PointerSensor, useSensor, useSensors } from '@dnd-kit/core'

import * as api from './api.js'
import Zone from './components/Zone.jsx'
import Chip from './components/Chip.jsx'
import ScoreDisplay from './components/ScoreDisplay.jsx'
import UnassignedPool, { UNASSIGNED } from './components/UnassignedPool.jsx'

const HISTORY_LIMIT = 50   // the brief asks for at least 20 steps

export default function App() {
  const [categories, setCategories] = useState([])
  const [zones, setZones] = useState([])
  const [layouts, setLayouts] = useState({ existing: null, proposed: null })

  const [assignment, setAssignment] = useState({})
  const [past, setPast] = useState([])
  const [future, setFuture] = useState([])

  const [score, setScore] = useState(null)
  const [prevScore, setPrevScore] = useState(null)
  const [markers, setMarkers] = useState([])
  const [error, setError] = useState(null)
  const [dragging, setDragging] = useState(null)
  const [diff, setDiff] = useState(null)

  const scoreSeq = useRef(0)

  // ---------------------------------------------------------------- load
  useEffect(() => {
    let cancelled = false
    async function boot() {
      try {
        const [cats, zs, existing, proposed, optimal] = await Promise.all([
          api.getCategories(), api.getZones(),
          api.getExistingLayout(), api.getProposedLayout(),
          api.getOptimalLayout(),
        ])
        if (cancelled) return
        setCategories(cats.categories)
        setZones(zs.zones)
        setLayouts({
          existing: existing.assignment,
          proposed: proposed.assignment,
          optimal: optimal.assignment,
        })

        // Reference markers come from scoring the three real layouts, not
        // from hardcoded constants, so they track the analysis if it is
        // re-run. The best computed layout sits at 100%: the scoring metric
        // has no notion of shelf capacity, so its optimum is one mega-zone.
        const [exScore, prScore, opScore] = await Promise.all([
          api.scoreLayout(existing.assignment),
          api.scoreLayout(proposed.assignment),
          api.scoreLayout(optimal.assignment),
        ])
        if (cancelled) return
        setMarkers([
          { value: exScore.capture_rate, label: 'current store layout' },
          { value: prScore.capture_rate, label: "algorithm's layout" },
          { value: opScore.capture_rate, label: 'best computed layout' },
        ])
        setAssignment(existing.assignment)
      } catch (err) {
        if (!cancelled) setError(err.message)
      }
    }
    boot()
    return () => { cancelled = true }
  }, [])

  // --------------------------------------------------------------- score
  useEffect(() => {
    if (categories.length === 0) return
    const seq = ++scoreSeq.current
    api.scoreLayout(assignment)
      .then((s) => {
        // Ignore a stale response that arrives after a newer one.
        if (seq !== scoreSeq.current) return
        setScore((current) => { setPrevScore(current); return s })
      })
      .catch((err) => setError(err.message))
  }, [assignment, categories.length])

  // ------------------------------------------------------------- history
  const commit = useCallback((next) => {
    setPast((p) => [...p, assignment].slice(-HISTORY_LIMIT))
    setFuture([])
    setAssignment(next)
    setDiff(null)
  }, [assignment])

  const undo = useCallback(() => {
    setPast((p) => {
      if (p.length === 0) return p
      const prev = p[p.length - 1]
      setFuture((f) => [assignment, ...f].slice(0, HISTORY_LIMIT))
      setAssignment(prev)
      return p.slice(0, -1)
    })
  }, [assignment])

  const redo = useCallback(() => {
    setFuture((f) => {
      if (f.length === 0) return f
      setPast((p) => [...p, assignment].slice(-HISTORY_LIMIT))
      setAssignment(f[0])
      return f.slice(1)
    })
  }, [assignment])

  useEffect(() => {
    const onKey = (e) => {
      if (!(e.ctrlKey || e.metaKey)) return
      if (e.key === 'z' && !e.shiftKey) { e.preventDefault(); undo() }
      if (e.key === 'y' || (e.key === 'z' && e.shiftKey)) { e.preventDefault(); redo() }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [undo, redo])

  // ---------------------------------------------------------------- drag
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
  )

  function onDragEnd(event) {
    setDragging(null)
    const { active, over } = event
    if (!over) return
    const category = active.id
    const target = over.id
    const currentZone = assignment[category] ?? UNASSIGNED
    if (currentZone === target) return

    const next = { ...assignment }
    if (target === UNASSIGNED) delete next[category]
    else next[category] = target
    commit(next)
  }

  // -------------------------------------------------------------- resets
  const resetEmpty = () => commit({})
  const resetExisting = () => layouts.existing && commit({ ...layouts.existing })
  const resetProposed = () => layouts.proposed && commit({ ...layouts.proposed })
  const loadOptimal = () => layouts.optimal && commit({ ...layouts.optimal })

  function revealAlgorithm() {
    if (!layouts.proposed) return
    const differences = categories
      .map((c) => ({
        name: c.name,
        yours: assignment[c.name] ?? UNASSIGNED,
        algorithm: layouts.proposed[c.name] ?? UNASSIGNED,
        inert: !c.appears_in_strong_rules,
      }))
      .filter((d) => d.yours !== d.algorithm)
    setDiff(differences)
    setPast((p) => [...p, assignment].slice(-HISTORY_LIMIT))
    setFuture([])
    setAssignment({ ...layouts.proposed })
  }

  // ------------------------------------------------------------ derived
  const byName = useMemo(
    () => Object.fromEntries(categories.map((c) => [c.name, c])),
    [categories],
  )

  const inZone = useCallback(
    (zoneId) => categories.filter((c) => (assignment[c.name] ?? UNASSIGNED) === zoneId),
    [categories, assignment],
  )

  const capturedByZone = useMemo(() => {
    if (!score) return {}
    const counts = {}
    for (const r of score.captured_rules) {
      counts[r.zone_id] = (counts[r.zone_id] ?? 0) + 1
    }
    return counts
  }, [score])

  const lostRules = useMemo(() => {
    if (!score || !prevScore) return []
    if (score.rules_captured >= prevScore.rules_captured) return []
    const now = new Set(score.captured_rules.map((r) => r.label))
    return prevScore.captured_rules.filter((r) => !now.has(r.label))
  }, [score, prevScore])

  const delta = score && prevScore ? score.rules_captured - prevScore.rules_captured : null
  const zoneName = (id) => (id === UNASSIGNED ? 'Unassigned' : zones.find((z) => z.id === id)?.name ?? id)
  const diffSet = useMemo(() => new Set((diff ?? []).map((d) => d.name)), [diff])

  if (error) {
    return (
      <main>
        <h1>Shelf Layout Tool</h1>
        <div className="error">
          <strong>Could not reach the API.</strong>
          <p>{error}</p>
          <p>Check it is running: <code>docker compose ps api</code></p>
        </div>
      </main>
    )
  }

  return (
    <main>
      <header className="top">
        <div>
          <h1>Shelf Layout Tool</h1>
          <p className="sub">
            Drag categories between zones. The score is the share of strong
            cross-sell rules your layout places together.
          </p>
        </div>
      </header>

      <ScoreDisplay score={score} markers={markers} delta={delta} lostRules={lostRules} />

      <div className="toolbar">
        <button onClick={undo} disabled={past.length === 0}>Undo ({past.length})</button>
        <button onClick={redo} disabled={future.length === 0}>Redo ({future.length})</button>
        <span className="sep" />
        <button onClick={resetEmpty}>Reset to empty</button>
        <button onClick={resetExisting}>Reset to existing</button>
        <button onClick={resetProposed}>Reset to proposed</button>
        <button onClick={loadOptimal} title="The optimiser's answer: every rule-bearing category in one zone. The metric has no notion of shelf space; that is the finding.">Load best computed</button>
        <span className="sep" />
        <button className="primary" onClick={revealAlgorithm}>Reveal the algorithm's layout</button>
      </div>

      {diff && (
        <div className="diff">
          <strong>
            {diff.length === 0
              ? 'Your layout already matched the algorithm exactly.'
              : `The algorithm placed ${diff.length} categor${diff.length === 1 ? 'y' : 'ies'} differently:`}
          </strong>
          {diff.length > 0 && (
            <table>
              <thead>
                <tr><th>Category</th><th>You had</th><th>Algorithm</th></tr>
              </thead>
              <tbody>
                {diff.map((d) => (
                  <tr key={d.name} className={d.inert ? 'diff-inert' : ''}>
                    <td>{d.name}{d.inert && <span className="chip-flag">no rules</span>}</td>
                    <td>{zoneName(d.yours)}</td>
                    <td>{zoneName(d.algorithm)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <button className="link" onClick={() => setDiff(null)}>Dismiss</button>
        </div>
      )}

      <DndContext
        sensors={sensors}
        onDragStart={(e) => setDragging(e.active.id)}
        onDragEnd={onDragEnd}
        onDragCancel={() => setDragging(null)}
      >
        <div className="zones">
          {zones.map((z) => (
            <Zone
              key={z.id}
              zone={z}
              categories={inZone(z.id)}
              capturedCount={capturedByZone[z.id] ?? 0}
              movedSet={diffSet}
            />
          ))}
        </div>

        <UnassignedPool categories={inZone(UNASSIGNED)} movedSet={diffSet} />

        <DragOverlay>
          {dragging && byName[dragging]
            ? <Chip category={byName[dragging]} />
            : null}
        </DragOverlay>
      </DndContext>

      <footer className="foot">
        <p>
          Scores come from <code>analysis/cross_sell.py</code>, the same function
          that produces the figures in the dissertation.
        </p>
      </footer>
    </main>
  )
}

