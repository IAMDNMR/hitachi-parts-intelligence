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
    statement: 'Service begins by understanding machine condition, before anything is touched.',
    systems: {
      consite: 'Condition reported by the machine as it works.',
      globalService: 'Inspection history, wherever the machine is.',
    },
  },
  {
    id: 'diagnose',
    index: '02',
    icon: 'diagnose',
    title: 'Diagnose',
    headline: ['Find the cause,', 'not the symptom.'],
    headlineAccent: 'The machine tells us.',
    statement: 'Machine information identifies what actually needs attention, and what does not.',
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
    statement: 'Genuine parts and trained expertise, combined into one service action.',
    systems: {
      consite: 'The record the machine kept, informing the repair.',
      globalService: 'Parts identification and dealer support.',
    },
  },
  {
    id: 'backToWork',
    index: '05',
    icon: 'uptime',
    title: 'Back to work',
    headline: ['Downtime ends.', 'The machine'],
    headlineAccent: 'goes back to work.',
    statement: 'The machine is returned to productive operation, ready for the next shift.',
    systems: {
      consite: 'Monitoring continues once it is working again.',
      globalService: 'Support that carries on through its life.',
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
 * `key` is the field read off the step; `id` is only the React key.
 */
export const serviceSystems = [
  { id: 'consite', key: 'consite', icon: 'consite', name: 'ConSite' },
  {
    id: 'global-e-service',
    key: 'globalService',
    icon: 'globalservice',
    name: 'Global Service',
  },
]
