import { useDroppable } from '@dnd-kit/core'
import Chip from './Chip.jsx'

/**
 * A droppable zone.
 *
 * The ethics classification is rendered on the zone header, not hidden in a
 * tooltip, because the dissertation argues the influence boundary should be
 * explicit to whoever is designing the layout.
 */
export default function Zone({ zone, categories, capturedCount, movedSet }) {
  const { setNodeRef, isOver } = useDroppable({ id: zone.id })

  const creates = zone.ethics === 'creates'

  return (
    <section
      ref={setNodeRef}
      className={`zone ${isOver ? 'zone-over' : ''} ${creates ? 'zone-creates' : 'zone-assists'}`}
    >
      <header className="zone-head">
        <div>
          <h3>{zone.name}</h3>
          <p className="zone-role">{zone.role}</p>
        </div>
        <div className="zone-meta">
          <span className="zone-count">{categories.length}</span>
          {capturedCount != null && (
            <span className="zone-captured">{capturedCount} rules</span>
          )}
        </div>
      </header>

      <p className={`ethics-tag ${creates ? 'ethics-creates' : 'ethics-assists'}`}
         title={zone.ethics_explanation}>
        {zone.ethics_label}
      </p>

      <div className="zone-body">
        {categories.length === 0 && <p className="zone-empty">Drop categories here</p>}
        {categories.map((c) => (
          <Chip key={c.name} category={c} moved={movedSet?.has(c.name)} />
        ))}
      </div>
    </section>
  )
}
