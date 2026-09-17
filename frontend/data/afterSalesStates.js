/**
 * Section 02's four ecosystem states.
 *
 * One machine, read four ways: what it reports, what it needs, what keeps it
 * working, and who stands behind it. Network is a state of this story only —
 * it explains the idea and links to nothing; the Network experience is its
 * own page.
 *
 * `frame` is the index into the rotation sequence the state is keyed to —
 * frames 0, 23, 46 and 69 of the 71 that
 * backend/video-processing/extract_section02.py cuts out of
 * aftersales-eco.mp4. The machine turns continuously through all 71 as the
 * reader scrolls; these four are only where the copy changes.
 *
 * `marker` is where the state's marker sits on the machine, in fractions of
 * the frame's own box. Every frame shares one crop, so a fraction lands in
 * the same place on all of them. They are placed over the parts of the
 * silhouette that hold still across the arc — cab, counterweight, boom foot,
 * undercarriage — rather than over the boom tip, which sweeps.
 *
 * `icon` names come from sections/AfterSalesEcosystem/EcosystemIcons.jsx.
 */
export const afterSalesStates = [
  {
    id: 'machine-data',
    index: '01',
    icon: 'data',
    frame: 0,
    title: 'Machine Data',
    statement: 'Understand the machine',
    line: 'Operational data turns machine activity into actionable insight.',
    marker: { x: 0.42, y: 0.44 },
  },
  {
    id: 'parts',
    index: '02',
    icon: 'parts',
    frame: 23,
    title: 'Parts',
    statement: 'Know what the machine needs',
    line: 'Product and parts information connects the machine to the right component.',
    marker: { x: 0.16, y: 0.58 },
  },
  {
    id: 'service',
    index: '03',
    icon: 'service',
    frame: 46,
    title: 'Service',
    statement: 'Keep it working',
    line: 'Service information helps maintain performance and reduce downtime.',
    marker: { x: 0.33, y: 0.83 },
  },
  {
    id: 'network',
    index: '04',
    icon: 'network',
    frame: 69,
    title: 'Network',
    statement: 'Connect the support',
    line: 'Dealers and service teams bring the digital journey into the field.',
    marker: { x: 0.58, y: 0.5 },
  },
]
