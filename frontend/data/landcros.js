/**
 * LANDCROS — where the European range is heading.
 *
 * Hitachi Construction Machinery takes the name LANDCROS in April 2027, and
 * Hitachi Construction Machinery (Europe) NV has shown two concept machines
 * under it. Neither is on sale and neither is in the 77-machine catalogue in
 * machineCatalogue.js, so they live here instead of in the taxonomy: the seven
 * categories stay exactly what HCME sells today.
 *
 * Hand-written, not generated, because there are two of them. Every line below
 * is taken from the official HCME Europe page named beside it; nothing is
 * worded into a claim those pages do not make. Images are the official files
 * recorded in HITACHI_MACHINE_IMAGES/LANDCROS/LANDCROS_IMAGE_MANIFEST.xlsx,
 * served as the web renditions scripts/build-web-images.py writes.
 */

const EU = 'https://www.hitachicm.com/eu/en'

const photo = (folder, stem, w, h, alt) => {
  const base = `/machines/LANDCROS/${folder}/${stem}`
  return {
    src: `${base}-1600.jpg`,
    srcset: [480, 960, 1600].map((px) => `${base}-${px}.jpg ${px}w`).join(', '),
    w,
    h,
    alt,
  }
}

export const LANDCROS = {
  /* press-center/hitachi-construction-machinery-rebrands-as-landcros, 28 Oct
     2025: "…its transformation and rebranding to LANDCROS, effective April
     2027." The tagline is the release's own sign-off. */
  rebrand: 'From April 2027, Hitachi Construction Machinery becomes LANDCROS.',
  tagline: 'Solutions beyond machinery',
  rebrandSource: `${EU}/press-center/hitachi-construction-machinery-rebrands-as-landcros/`,

  concepts: [
    {
      id: 'landcros-one',
      name: 'LANDCROS One',
      kind: 'Excavator concept',
      /* unveils-landcros-one…bauma-2025, 07 Apr 2025: "LANDCROS One showcases
         Hitachi's vision of a safer, smarter, and more sustainable future";
         developed with Granstudio (same release and the Red Dot article). */
      lead: 'A vision of a safer, smarter and more sustainable future, developed with the design studio Granstudio.',
      /* landcros-one-lands-prestigious-red-dot-design-award, 01 Jul 2025. */
      specs: [
        { icon: 'event', label: 'Unveiled', value: 'bauma, Munich, April 2025' },
        { icon: 'power', label: 'Power', value: 'Electric, diesel or hydrogen' },
        { icon: 'operation', label: 'Operation', value: 'Manual, AI-assisted or autonomous' },
        { icon: 'award', label: 'Recognition', value: '2025 Red Dot Design Award' },
      ],
      source: `${EU}/onsite/article/landcros-one-lands-prestigious-red-dot-design-award/`,
      gallery: [
        photo('LANDCROS_One', '62011_Landcros_Cover', 1920, 1428,
          'LANDCROS One concept excavator standing on rock, drones overhead'),
        photo('LANDCROS_One', 'LANDCROS_One_REDDOT-winner', 1920, 1080,
          'LANDCROS One in the studio, marked as a Red Dot winner 2025'),
        photo('LANDCROS_One', 'LANDCROS-One-P6A4907', 1920, 1281,
          'LANDCROS One on the Hitachi stand at bauma 2025'),
        photo('LANDCROS_One', 'LANDCROS-One-DSC01057', 1920, 1280,
          'Close view of the LANDCROS One body and tracks'),
        photo('LANDCROS_One', 'Landcros_One_on_HCME_stand', 1920, 1280,
          'LANDCROS One on the HCME stand, seen from the front'),
      ],
    },
    {
      id: 'landcros-mini',
      name: 'LANDCROS Mini',
      kind: 'Five-tonne concept excavator',
      /* LANDCROS-Mini-Takes-Honours-at-SaMoTer-2026, 06 May 2026: "The cab is
         shaped around the human, not the other way around." */
      lead: 'A compact excavator whose cab is shaped around the operator, not the other way around.',
      /* landcros-mini-concept-excavator-stands-out-at-Samoter, 12 May 2026. */
      specs: [
        { icon: 'event', label: 'Shown', value: 'SaMoTer, Verona, May 2026' },
        { icon: 'weight', label: 'Class', value: 'Five tonnes' },
        { icon: 'view', label: 'Cab', value: '360-degree view, people-detection lighting' },
        { icon: 'award', label: 'Recognition', value: 'SaMoTer Design Award and Technical Mention' },
      ],
      source: `${EU}/onsite/article/landcros-mini-concept-excavator-stands-out-at-Samoter/`,
      gallery: [
        photo('LANDCROS_Mini', 'Landcros-Mini_still-image', 1920, 1080,
          'LANDCROS Mini concept excavator in a dark studio'),
        photo('LANDCROS_Mini', 'LANDCROS_mini_2', 1920, 1280,
          'LANDCROS Mini on the HCME stand at SaMoTer 2026'),
        photo('LANDCROS_Mini', 'LANDCROS_mini_1', 1920, 1280,
          'Visitors around the LANDCROS Mini at SaMoTer 2026'),
        photo('LANDCROS_Mini', 'LANDCROS_mini_4', 1920, 1280,
          'An operator climbing into the LANDCROS Mini cab'),
        photo('LANDCROS_Mini', 'LANDCROS_mini_3', 1920, 1280,
          'The LANDCROS Mini cab display and controls'),
      ],
    },
  ],

  /* Each date is the one the linked HCME Europe page gives. */
  timeline: [
    { date: '2024-07', label: 'Jul 2024', text: 'LANDCROS launched as an innovation initiative',
      source: `${EU}/press-center/HCM_Launches_LANDCROS/` },
    { date: '2025-04', label: 'Apr 2025', text: 'LANDCROS One unveiled at bauma, Munich',
      source: `${EU}/press-center/hitachi-construction-machinery-europe-unveils-landcros-one-excavator-concept-at-bauma-2025/` },
    { date: '2025-07', label: 'Jul 2025', text: 'LANDCROS One wins a Red Dot Design Award',
      source: `${EU}/press-center/landcros-one-lands-prestigious-red-dot-design-award/` },
    { date: '2026-01', label: 'Jan 2026', text: 'LANDCROS Development Center Europe opens in Germany',
      source: `${EU}/press-center/hitachi-construction-machinery-establishes-landcros-development-center-europe/` },
    { date: '2026-05', label: 'May 2026', text: 'LANDCROS Mini shown at SaMoTer, Verona',
      source: `${EU}/press-center/LANDCROS-Mini-Takes-Honours-at-SaMoTer-2026/` },
    { date: '2027-04', label: 'Apr 2027', text: 'Hitachi Construction Machinery becomes LANDCROS',
      source: `${EU}/press-center/hitachi-construction-machinery-rebrands-as-landcros/` },
  ],

  /* The EU homepage carousel slide "LANDCROS Connect" links to this page. */
  connect: {
    name: 'LANDCROS Connect',
    line: "HCME's fleet management system",
    href: `${EU}/service/fleet-management/fleet-management-system-connect/`,
  },
}
