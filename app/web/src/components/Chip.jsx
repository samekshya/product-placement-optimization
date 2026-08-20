import { useDraggable } from '@dnd-kit/core'

/**
 * A draggable category chip.
 *
 * Chips for categories with no strong rule are visually distinct and carry a
 * tooltip. Without that, a user who moves several of them and sees the score
 * stay still concludes the tool is broken, when in fact those categories carry
 * no association at lift 3.0 and cannot move the number.
 */
export default function Chip({ category, moved }) {
  const { attributes, listeners, setNodeRef, transform, isDragging } =
    useDraggable({ id: category.name })

  const inert = !category.appears_in_strong_rules

  const style = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` }
    : undefined

  const title = inert
    ? `${category.name}: appears in no rule at lift 3.0 or above, so moving it ` +
      `cannot change the score. It is ${category.basket_penetration_pct}% of baskets.`
    : `${category.name}: ${category.basket_penetration_pct}% of baskets, ` +
      `carries at least one strong rule.`

  const classes = [
    'chip',
    inert ? 'chip-inert' : 'chip-active',
    isDragging ? 'chip-dragging' : '',
    moved ? 'chip-moved' : '',
  ].filter(Boolean).join(' ')

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={classes}
      title={title}
      {...listeners}
      {...attributes}
    >
      <span className="chip-name">{category.name}</span>
      <span className="chip-pct">{category.basket_penetration_pct}%</span>
      {inert && <span className="chip-flag" aria-label="no strong rules">no rules</span>}
    </div>
  )
}
