/**
 * Pure logic for how a part relates to a selected machine — split out from
 * PartsStore.jsx so it can be tested without rendering React.
 *
 * `part.fitment` is a flat list of `{ machineId, level }` rows, one per real
 * 5_MACHINE_PARTS row for that part — not a per-part summary — because a
 * part can be EXACT MODEL for some machines and MODEL/RANGE for others (two
 * of the real batteries are). `level` is the workbook's own vocabulary:
 * EXACT MODEL, MODEL/RANGE or CATEGORY. A part with no `fitment` array at
 * all (the original 10 showcase parts, which predate the workbook import)
 * carries no compatibility data — that is a data gap, not evidence the part
 * doesn't fit, so it is never reported as incompatible.
 */
export const levelLabel = {
  exact: 'Exact model',
  range: 'Model range',
  category: 'Category-level',
  general: 'General part family',
}

export function groupForCategory(category) {
  if (category.includes('Lubricants')) return 'Lubricants'
  if (category.includes('Attachments')) return 'Attachments'
  if (category.includes('Wheel Loader')) return category
  return category
}

export function relationshipFor(part, machine) {
  if (!machine) return { level: 'general', text: 'Select a machine to check applicability' }
  if (!part.fitment) return { level: 'general', text: 'General part family. Confirm fitment before ordering.' }
  const row = part.fitment.find((f) => f.machineId === machine.id)
  if (!row) return { level: 'general', text: 'No confirmed compatibility for the selected machine.' }
  if (row.level === 'EXACT MODEL') {
    return { level: 'exact', text: `Exact model fitment for ${machine.model}` }
  }
  if (row.level === 'MODEL/RANGE') {
    return {
      level: 'range',
      text: `Model-range fitment for ${machine.model} — base model published, configuration variant not stated`,
    }
  }
  return {
    level: 'category',
    text: `Associated product line for ${machine.model} — not published as verified fitment`,
  }
}
