/**
 * The after-sales domains, each tied to a real part of the machine.
 *
 * COORDINATE SYSTEMS — two of them, deliberately:
 *
 *   `anchor` is in **video-frame** space (0..1 of the clip's own 1280x720
 *   frame). It points at an actual component in the separated machine, so the
 *   connection line starts where that component is on screen no matter how
 *   the video is fitted to the viewport.
 *
 *   `card` is in **stage** space (0..1 of the viewport). Cards sit in the
 *   clear floor band below the separated machine, which is a position on
 *   screen rather than a position in the clip.
 *
 * useStageFit converts between the two.
 *
 * `reveal` is the progress value at which the component has visibly separated
 * enough for its label to make sense — the labels arrive with the machine
 * coming apart, not on a timer of their own.
 *
 * `groundId` is the node in src/ground/data/graph.ts this domain becomes once
 * the reader wants the architecture behind it. The panel used to end with
 * "Detailed view in development", which was true when it was written and
 * stopped being true when The Ground was built — the deeper view exists, and
 * every one of these six has a node waiting for it. Written here rather than
 * mapped in the component so the pairing is data someone can check against
 * the graph, and so a renamed node breaks in one obvious place.
 */
export const ecosystemNodes = [
  {
    id: 'service',
    groundId: 'service',
    label: 'SERVICE',
    component: 'Operator cab',
    icon: 'service',
    reveal: 0.4,
    anchor: { x: 0.25, y: 0.52 },
    card: { x: 0.17, y: 0.85 },
    panel: {
      title: 'Service',
      lead: 'Planned maintenance, diagnostics and repair delivered through the dealer network.',
      points: [
        'Scheduled and condition-based maintenance',
        'Field service and workshop repair',
        'Technician diagnostics and repair guidance',
      ],
    },
  },
  {
    id: 'parts',
    groundId: 'parts',
    label: 'PARTS',
    component: 'Boom and arm',
    icon: 'parts',
    reveal: 0.43,
    anchor: { x: 0.34, y: 0.3 },
    card: { x: 0.31, y: 0.85 },
    panel: {
      title: 'Parts',
      lead: 'Genuine parts, remanufactured units and consumables for the installed base.',
      points: [
        'Genuine, reman and value-line part ranges',
        'Part identification from machine serial number',
        'Availability across the distribution network',
      ],
    },
  },
  {
    id: 'dealer-network',
    groundId: 'network',
    label: 'DEALER NETWORK',
    component: 'Undercarriage',
    icon: 'network',
    reveal: 0.46,
    anchor: { x: 0.44, y: 0.76 },
    card: { x: 0.45, y: 0.85 },
    panel: {
      title: 'Dealer Network',
      lead: 'The dealers and branches that carry the customer relationship day to day.',
      points: [
        'Local stock, workshops and field engineers',
        'Shared systems between HCME and dealers',
        'The point where parts and service reach the machine',
      ],
    },
  },
  {
    id: 'machine-data',
    groundId: 'machine-data',
    label: 'MACHINE DATA',
    component: 'Hydraulic pump',
    icon: 'data',
    reveal: 0.49,
    anchor: { x: 0.71, y: 0.28 },
    card: { x: 0.62, y: 0.85 },
    panel: {
      title: 'Machine Data',
      lead: 'Operating and condition data that turns after-sales from reactive to planned.',
      points: [
        'Operating hours and machine condition',
        'Alerts and fault codes from the field',
        'Input to service planning and parts demand',
      ],
    },
  },
  {
    id: 'warranty',
    groundId: 'warranty',
    label: 'WARRANTY',
    component: 'Upper structure',
    icon: 'warranty',
    reveal: 0.52,
    anchor: { x: 0.82, y: 0.53 },
    card: { x: 0.76, y: 0.85 },
    panel: {
      title: 'Warranty',
      lead: 'Claims, coverage and product support across the machine lifecycle.',
      points: [
        'Standard and extended coverage',
        'Claim submission, assessment and settlement',
        'Failure data feeding back into product quality',
      ],
    },
  },
  {
    id: 'logistics',
    groundId: 'n-warehouses',
    label: 'LOGISTICS',
    component: 'Final drive',
    icon: 'logistics',
    reveal: 0.55,
    anchor: { x: 0.81, y: 0.76 },
    card: { x: 0.9, y: 0.85 },
    panel: {
      title: 'Logistics',
      lead: 'Moving the right part from the warehouse to the machine.',
      points: [
        'Central and regional parts warehousing',
        'Replenishment and emergency order flows',
        'Transport to dealer, site or technician',
      ],
    },
  },
]

/** Connections hold while the ecosystem and Parts & Services states are read. */
export const CONNECTIONS_FADE_OUT = [0.66, 0.7]
