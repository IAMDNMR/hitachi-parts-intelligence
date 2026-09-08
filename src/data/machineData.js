/**
 * Machine identification only.
 *
 * Deliberately not a telemetry panel: no hours, no service intervals, no
 * status readouts. Anything quantitative here would read as a measurement
 * taken from a real machine, and would turn the hero into a dashboard.
 */
export const MACHINE_ID = {
  label: 'MACHINE',
  value: 'ZX350LC-7',
}
