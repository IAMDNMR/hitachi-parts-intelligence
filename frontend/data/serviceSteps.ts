/**
 * Section 04's service stages, in the order the work actually happens.
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
 * This is dealership after-sales service. The footage behind stages 01-04
 * (section-4.mp4, frames 1-72) is a single continuous shot in the dealer
 * workshop — genuine service activity (handset, panels, filters, tools),
 * but a workshop, not the machine's own work site. The copy for those four
 * stages is written to match that honestly: it describes the service
 * process, not a claim that the technician travelled to the machine in the
 * field. Only stage 05's footage (frames 73-90, a separate outdoor clip) is
 * actually a work site, which is why it alone earns that language. See
 * SERVICE_FUTURE_ASSETS.md for what outdoor service footage would be needed
 * to honestly tell the field-service version of this story.
 *
 * The stage's own frames come from assets/source/section-04/, keyed by
 * service-frame-map.json rather than by anything written here — `id` matches
 * the map's stage keys, so the two cannot drift apart.
 *
 * `icon` names come from sections/ServiceExperience/ServiceIcons.jsx.
 *
 * The `field` pre-stage is an establishing beat that plays outdoor footage
 * BEFORE the numbered journey begins. It reuses the same outdoor frames
 * (73-90) that `backToWork` uses at the end, but scrubs only the first
 * portion (frames 73-84) to create a distinct treatment. It is NOT a
 * numbered service stage — the right-side navigation skips it entirely.
 */
export const serviceSteps = [
  {
    id: 'field',
    index: null,
    icon: 'uptime',
    title: null,
    isFieldBeat: true,
    headline: ['The machine', 'is at work.'],
    headlineAccent: null,
    statement: 'When it needs attention, service begins.',
    systems: {
      consite: 'Condition reported by the machine as it works.',
      globalService: 'Service history, wherever the machine is.',
    },
  },
  {
    id: 'inspect',
    index: '01',
    icon: 'inspect',
    title: 'Inspect',
    headline: ['The machine needs', 'more than parts.'],
    headlineAccent: 'It needs support.',
    statement:
      'A machine needs attention. The service process begins with inspection — understanding its condition before anything is touched.',
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
      'In the dealer workshop, the technician traces the cause using the machine\u2019s own data, before any panel is opened.',
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
    statement:
      'Filters, fluids and components, checked and serviced at the right interval — protecting performance before it is compromised.',
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
    headlineAccent: 'Service and repair.',
    statement:
      'Required parts are identified, and the technician completes the service in the workshop.',
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

/** The service stages that appear in the right-side navigation (numbered 01–05). */
export const serviceNavSteps = serviceSteps.filter((s) => !s.isFieldBeat)

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
