import type { Category, Machine } from '../../data/machineCatalogue'

/**
 * What the model showcase says about a machine.
 *
 * The picture is not chosen here: each machine carries one isolated hero
 * asset, picked by eye and built by scripts/build-hero-assets.py.
 *
 * Pure functions over one catalogue record, kept out of the component so they
 * can be tested and so the showcase itself holds no rules about data. Nothing
 * here invents a value: every line is a field from the frozen workbook, and a
 * field the workbook marks as not stated is left out rather than filled in.
 */

/** A value the workbook records as unknown, or no value at all. */
function missing(v: unknown): boolean {
  return !v || !String(v).trim() || /not (publicly )?stated|^n\/?a$|^[-—]$/i.test(String(v).trim())
}

/**
 * The name, split where Special Applications carries its application in
 * front: "Demolition — ZX390TC-7" becomes a kicker "Demolition" over the name
 * "ZX390TC-7", so the reader sees what the machine is for and which one it is.
 */
export function nameParts(machine: Machine): { kicker: string | null; name: string } {
  const label = machine.displayLabel || machine.name
  const i = label.indexOf(' — ')
  if (i === -1) return { kicker: null, name: label }
  return { kicker: label.slice(0, i), name: label.slice(i + 3) }
}

const applications = (machine: Machine): string[] =>
  missing(machine.application)
    ? []
    : String(machine.application).split(';').map((s) => s.trim()).filter(Boolean)

/**
 * One short line about the machine, assembled only from its own fields:
 * power type, machine type and applications. "Diesel hydraulic excavator for
 * earthmoving, construction, mining and quarrying." If the record has no
 * applications the category's own description is used instead.
 *
 * At most three applications are named - a wheel loader lists nine, which made
 * a five-line paragraph of what should be one line. When there are more it
 * says so: "... and more".
 */
const STORY_APPS = 3

export function storyLine(machine: Machine, category: Category | null | undefined): string {
  const apps = applications(machine).map((a) => a.charAt(0).toLowerCase() + a.slice(1))
  if (!apps.length || missing(machine.machineType)) return category?.blurb || ''
  let list
  if (apps.length > STORY_APPS) list = `${apps.slice(0, STORY_APPS).join(', ')} and more`
  else list = apps.length > 1 ? `${apps.slice(0, -1).join(', ')} and ${apps.at(-1)}` : apps[0]
  const kind = String(machine.machineType).toLowerCase()
  const lead = missing(machine.powerType) ? kind : `${machine.powerType} ${kind}`
  return `${lead.charAt(0).toUpperCase()}${lead.slice(1)} for ${list}.`
}

/** "Large Excavators" -> "Large Excavator"; "Rigid Dump Trucks" -> "Rigid Dump Truck". */
function singular(label: string): string {
  return label.replace(/s$/, '')
}

/* The European range reads in metric. Some records carry an imperial
   conversion after the kilograms - "322 000 kg (709,888 lb.)" - and only the
   workbook's own metric figure is kept. */
const metric = (v: unknown): string => String(v).replace(/\s*\([\d.,\s]+lbs?\.?\)\s*$/i, '').trim()

/** A power figure short enough to read at a glance, e.g. "296 kW". */
export const SHORT_POWER = 24

export interface InfoRow {
  key: string
  label: string
  value: string
}

/**
 * The facts on the right: category and model, then at most two more - the
 * operating weight, and the power when the workbook states it briefly. Each
 * appears only if the workbook states it; nothing is added and nothing
 * estimated. Labels are what the value actually is: the workbook records an
 * operating weight, so it is called that and not a "class".
 *
 * Deliberately not a specification sheet. Where the recorded power is a long
 * multi-engine string ("Standard: Cummins QSKTA60-CE 2 125 kW ... / Optional:
 * MTU ..."), the panel gives the drive type instead - still the workbook's
 * own value, just the short one. Applications are left to the line under the
 * name.
 */
export function infoRows(machine: Machine): InfoRow[] {
  const rows: InfoRow[] = []
  if (!missing(machine.subcategory)) rows.push({ key: 'category', label: 'Category', value: singular(String(machine.subcategory)) })
  if (machine.modelsCovered?.length) rows.push({ key: 'model', label: 'Model', value: machine.modelsCovered.join(' / ') })
  if (!missing(machine.operatingWeight)) rows.push({ key: 'weight', label: 'Operating weight', value: metric(machine.operatingWeight) })
  const power = missing(machine.power) ? '' : String(machine.power).trim()
  if (power && power.length <= SHORT_POWER) {
    const drive = missing(machine.powerType) ? '' : ` · ${machine.powerType}`
    rows.push({ key: 'power', label: 'Power', value: `${power}${drive}` })
  } else if (!missing(machine.powerType)) {
    rows.push({ key: 'power', label: 'Drive', value: String(machine.powerType) })
  }
  return rows
}
