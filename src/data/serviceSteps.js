/**
 * Section 04's five service stages, in the order the work actually happens.
 *
 * They are written as one process rather than five offers. Each stage owns
 * the whole of the left column: its own headline, set in two dark lines and
 * one orange, and its own supporting line. The stage NAME is deliberately
 * not repeated there — the journey on the right already names it, and
 * printing "MAINTAIN" twice on one screen was the section's loudest
 * redundancy.
 *
 * Stage 01 carries the section's thesis, so the argument the section exists
 * to make is the first thing read and the rest of the copy develops it.
 *
 * There are no figures here — no response times, no uptime percentages, no
 * fault counts — because the project holds no service data to support them.
 *
 * This is dealership after-sales service, not a machine's trip to a
 * building. The dealer service team follows the machine — a technician
 * diagnoses it where it is, and only where the job needs a workshop does the
 * machine come to one. Stage 01 carries that: a service need is raised and
 * reaches the dealer before anything is touched. It is folded into Inspect
 * rather than given a stage of its own, because the section's five stages
 * are cut to five ranges of footage (service-frame-map.json) and a sixth
 * stage has no footage to draw from yet — the model is correct here even
 * though the frame count is not, and expanding it is future work, not a
 * rewrite this pass is scoped to do.
 *
 * The stage's own frames come from assets/source/section-04/, keyed by
 * service-frame-map.json rather than by anything written here — `id` matches
 * the map's stage keys, so the two cannot drift apart.
 *
 * `icon` names come from sections/ServiceExperience/ServiceIcons.jsx.
 */
export const serviceSteps = [
  {
    id: 'inspect',
    index: '01',
    icon: 'inspect',
    title: 'Inspect',
    headline: ['The machine needs', 'more than parts.'],
    headlineAccent: 'It needs support.',
    statement:
      'A machine needs attention. The dealer service team receives the need, and inspection begins before anything is touched.',
    systems: {
      consite: 'Condition reported by the machine as it works.',
      globalService: 'Service history, wherever the machine is.',
    },
  },
  {
    id: 'diagnose',
    index: '02',
    icon: 'diagnose',
    title: 'Diagnose',
    headline: ['Find the cause,', 'not the symptom.'],
    headlineAccent: 'The machine tells us.',
    statement:
      'A technician diagnoses the machine where it is — or the machine is brought to a dealer workshop, when the job requires it.',
    systems: {
      consite: 'Operating data that points at the fault.',
      globalService: 'Technical information behind the diagnosis.',
    },
  },
  {
    id: 'maintain',
    index: '03',
    icon: 'maintain',
    title: 'Maintain',
    headline: ['Service it before', 'it stops you.'],
    headlineAccent: 'Planned, not reactive.',
    statement: 'Maintenance at the right interval protects performance before it is compromised.',
    systems: {
      consite: 'Service alerts before an interval is missed.',
      globalService: 'Maintenance schedules and part references.',
    },
  },
  {
    id: 'repair',
    index: '04',
    icon: 'repair',
    title: 'Repair',
    headline: ['The right part,', 'fitted right.'],
    headlineAccent: 'First time.',
    statement:
      'Required parts are identified and fulfilled, and the technician completes the repair.',
    systems: {
      consite: 'The record the machine kept, informing the repair.',
      globalService: 'Technical reference data behind parts identification.',
    },
  },
  {
    id: 'backToWork',
    index: '05',
    icon: 'uptime',
    title: 'Back to work',
    headline: ['Downtime ends.', 'The machine'],
    headlineAccent: 'goes back to work.',
    statement: 'The machine is back at work, ready for the next shift.',
    systems: {
      consite: 'Monitoring continues once it is working again.',
      globalService: 'Machine information that carries on through its life.',
    },
  },
]

/**
 * The two Hitachi service capabilities named in this section.
 *
 * The names are fixed — they are products — but what each one is *doing*
 * changes with the stage, so the line under each name comes from the active
 * step's `systems` rather than from here. Two constant sentences sitting
 * under five changing stages read as a footer nobody had updated.
 *
 * Both are information capabilities, not the operational actor. The dealer
 * service team and its technicians do the work; ConSite and Global e-Service
 * are what informs them while they do it, which is why every `systems` line
 * above is written as data, history or reference — never as an action the
 * platform itself is taking.
 *
 * `key` is the field read off the step; `id` is only the React key.
 */
export const serviceSystems = [
  { id: 'consite', key: 'consite', icon: 'consite', name: 'ConSite' },
  {
    id: 'global-e-service',
    key: 'globalService',
    icon: 'globalservice',
    name: 'Global e-Service',
  },
]
