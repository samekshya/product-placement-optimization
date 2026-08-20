import { useDroppable } from '@dnd-kit/core'
import Chip from './Chip.jsx'

export const UNASSIGNED = 'unassigned'

/** Holding area for categories not yet placed in a zone. */
export default function UnassignedPool({ categories, movedSet }) {
  const { setNodeRef, isOver } = useDroppable({ id: UNASSIGNED })

  return (
    <section ref={setNodeRef} className={`pool ${isOver ? 'zone-over' : ''}`}>
      <header className="zone-head">
        <div>
          <h3>Unassigned</h3>
          <p className="zone-role">Not placed, cannot capture any rule</p>
        </div>
        <span className="zone-count">{categories.length}</span>
      </header>
      <div className="zone-body">
        {categories.length === 0 && <p className="zone-empty">Every category is placed</p>}
        {categories.map((c) => (
          <Chip key={c.name} category={c} moved={movedSet?.has(c.name)} />
        ))}
      </div>
    </section>
  )
}
