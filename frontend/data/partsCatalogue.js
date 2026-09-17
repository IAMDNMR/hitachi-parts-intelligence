/**
 * The first ten parts in parts-video.mp4, in the order the clip shows them.
 *
 * The order and the segment boundaries are not a guess: survey_parts.py
 * measured frame-to-frame difference across all 240 frames and found nine
 * hard cuts (spikes of 22-41 against a bed under 3) at frames 22, 46, 72,
 * 96, 120, 144, 168, 190 and 214. Each part was then identified by looking
 * at the frames themselves. The extractor keeps FRAMES_PER_PART evenly
 * spaced frames from each part's segment, so part i owns frames
 * [i * FRAMES_PER_PART, i * FRAMES_PER_PART + FRAMES_PER_PART - 1] and the
 * boundaries need no hand-written indices here — the copy always changes
 * exactly on the cut, by construction.
 *
 * WHAT THE COPY MAY SAY
 * ---------------------
 * There is no product metadata in this project, so nothing here states a
 * part number, a price, a machine it fits, a material, a tolerance or a
 * performance figure. Every description says only what the part is for,
 * which is true of the component on screen and needs no data sheet to
 * support it. `attributes` come from a fixed vocabulary of qualities that
 * apply to Hitachi genuine parts as a range — not to a specific SKU. They
 * are also meant to *differ* between parts: an attribute carried by all ten
 * tells the reader nothing, so "genuine" is stated once in the section's
 * supporting line rather than repeated on every chip.
 *
 * Items after the first ten come from HITACHI_AFTERSALES_ECOM_GRAPH_MASTER.xlsx,
 * sheets 4_PARTS and 5_MACHINE_PARTS. The relationships below preserve the
 * workbook's own applicability level: exact model means exact model, category
 * means category-level association only.
 */
const zwTransmissionOilImage = new URL(
  '../assets/parts/lubricants/zw-transmission-oil-10w.webp',
  import.meta.url,
).href
const zwAxleOilImage = new URL('../assets/parts/lubricants/zw-axle-oil.webp', import.meta.url).href
const gearOilImage = new URL('../assets/parts/lubricants/genuine-gear-oil.webp', import.meta.url).href
const greaseImage = new URL('../assets/parts/lubricants/genuine-grease-ep2.webp', import.meta.url).href
const tractionBatteryImage = new URL(
  '../assets/parts/batteries/battery-4663907.webp',
  import.meta.url,
).href
const remanufacturedComponentsImage = new URL(
  '../assets/parts/reman/remanufactured-components.webp',
  import.meta.url,
).href

export const partsCatalogue = [
  {
    id: 'hydraulic-cylinder',
    name: 'Hydraulic Cylinder',
    category: 'Hydraulics',
    description:
      'Delivers the boom, arm and bucket movement the machine works with, under demanding operating conditions.',
    attributes: ['exactfit', 'reliable'],
  },
  {
    id: 'hydraulic-pump',
    name: 'Hydraulic Pump',
    category: 'Hydraulics',
    description:
      'Supplies the flow that every hydraulic circuit on the machine depends on.',
    attributes: ['reliable', 'serviceable'],
  },
  {
    id: 'diesel-engine',
    name: 'Diesel Engine',
    category: 'Powertrain',
    description:
      'The complete engine assembly — the source of every kilowatt the machine puts to work.',
    attributes: ['serviceable', 'durable'],
  },
  {
    id: 'reduction-gear',
    name: 'Reduction Gear',
    category: 'Drivetrain',
    description:
      'Turns motor speed into the torque the tracks and the upper structure need to move.',
    attributes: ['exactfit', 'durable'],
  },
  {
    id: 'swing-bearing',
    name: 'Swing Bearing',
    category: 'Upper Structure',
    description:
      'The ring the whole upper structure turns on, carrying load in several directions at once.',
    attributes: ['durable', 'reliable'],
  },
  {
    id: 'bucket',
    name: 'Bucket',
    category: 'Front Attachment',
    description:
      'The working edge of the machine, where every cycle of digging force is finally delivered.',
    attributes: ['durable', 'serviceable'],
  },
  {
    id: 'track-assembly',
    name: 'Track Assembly',
    category: 'Undercarriage',
    description:
      'Shoes, links, rollers and idler — the undercarriage that carries the machine over the ground.',
    attributes: ['durable', 'exactfit'],
  },
  {
    id: 'filters',
    name: 'Genuine Filters',
    category: 'Maintenance Parts',
    description:
      'Fuel and oil filtration made to Hitachi specification — the simplest protection on the machine.',
    attributes: ['exactfit', 'available'],
  },
  {
    id: 'controller',
    name: 'Machine Controller',
    category: 'Electronics',
    description:
      'The control unit that coordinates the machine’s systems and reports what it finds.',
    attributes: ['exactfit', 'reliable'],
  },
  {
    id: 'fuel-injection-pump',
    name: 'Fuel Injection Pump',
    category: 'Engine System',
    description:
      'Meters and delivers fuel to the engine on every stroke of its working cycle.',
    attributes: ['reliable', 'serviceable'],
  },
  {
    id: 'traction-battery',
    name: 'Traction Battery',
    category: 'Electrical / Electric Machines',
    description:
      'Industrial traction battery coverage for the electric excavator models explicitly listed in the workbook.',
    attributes: ['exactfit', 'available'],
    image: tractionBatteryImage,
    imageSource: 'Hitachi Construction Machinery / Heavy Equipment Industrial Battery',
    relationships: [
      {
        level: 'exact-model',
        models: ['ZX55U-6EB', 'ZX85-6EB', 'ZX135-7EB'],
        sourceRows: ['4_PARTS PT-005/PT-008/PT-010', '5_MACHINE_PARTS exact model rows'],
      },
    ],
  },
  {
    id: 'zw-transmission-oil-10w',
    name: 'Hitachi Genuine ZW Transmission Oil 10W',
    category: 'Wheel Loader / Drivetrain',
    description:
      'Transmission oil associated at category level with the ZW wheel loader range in the workbook.',
    attributes: ['available', 'serviceable'],
    image: zwTransmissionOilImage,
    imageSource:
      'HCME Hitachi Genuine ZW transmission oil 10W page / Scene7 Gen-Transmission-Oil',
    relationships: [
      {
        level: 'category',
        models: ['ZW95-6', 'ZW140', 'ZW160-7', 'ZW180-7', 'ZW220-7', 'ZW250-7', 'ZW310-7'],
        sourceRows: ['4_PARTS PT-034', '5_MACHINE_PARTS category rows'],
      },
    ],
  },
  {
    id: 'zw-axle-oil',
    name: 'Hitachi Genuine Axle Oil (ZW-series)',
    category: 'Wheel Loader / Axle & Drivetrain',
    description:
      'Axle oil associated at category level with ZW wheel loaders, not presented as a model-specific SKU.',
    attributes: ['available', 'durable'],
    image: zwAxleOilImage,
    imageSource: 'HCME Hitachi Genuine Axle oil for ZW-series page / Scene7 Axle-oil',
    relationships: [
      {
        level: 'category',
        models: ['ZW95-6', 'ZW140', 'ZW160-7', 'ZW180-7', 'ZW220-7', 'ZW250-7', 'ZW310-7'],
        sourceRows: ['4_PARTS PT-033', '5_MACHINE_PARTS category rows'],
      },
    ],
  },
  {
    id: 'genuine-gear-oil',
    name: 'Hitachi Genuine Gear Oil',
    category: 'Lubricants / Drivetrain',
    description:
      'A broad drivetrain lubricant association across the machine universe, including rigid dump trucks at category level.',
    attributes: ['available', 'serviceable'],
    image: gearOilImage,
    imageSource: 'HCME Hitachi Genuine Gear oil page / Scene7 Gear-oil',
    relationships: [
      {
        level: 'category',
        models: ['All 77 workbook machine records'],
        sourceRows: ['4_PARTS PT-037', '5_MACHINE_PARTS category rows'],
      },
    ],
  },
  {
    id: 'genuine-grease-ep2',
    name: 'Hitachi Genuine Grease EP2',
    category: 'Lubricants / Maintenance',
    description:
      'A common maintenance lubricant associated at category level across the machine universe.',
    attributes: ['available', 'durable'],
    image: greaseImage,
    imageSource: 'HCME Hitachi Genuine Grease page / Scene7 Hitachi-Grease-line-up-16x9',
    relationships: [
      {
        level: 'category',
        models: ['All 77 workbook machine records'],
        sourceRows: ['4_PARTS PT-032', '5_MACHINE_PARTS category rows'],
      },
    ],
  },
  {
    id: 'remanufactured-components',
    name: 'Hitachi Remanufactured Components',
    category: 'Reman / Replacement Parts',
    description:
      'An after-sales replacement offering for remanufactured components, associated broadly but not as an exact component fitment.',
    attributes: ['serviceable', 'available'],
    image: remanufacturedComponentsImage,
    imageSource: 'Hitachi Genuine Remanufactured Components / Certified Factory Exchange Program',
    relationships: [
      {
        level: 'category',
        models: ['74 workbook machine records'],
        sourceRows: ['4_PARTS PT-024', '5_MACHINE_PARTS category rows'],
      },
    ],
  },
]

/**
 * Frames kept per part. Must match PER_PART in
 * backend/video-processing/extract_section03.py.
 */
export const FRAMES_PER_PART = 9

/**
 * The attribute vocabulary. Deliberately small and deliberately general —
 * these are qualities of the genuine parts range, not claims about a
 * particular component.
 */
export const partAttributes = {
  exactfit: { label: 'Exact fit', icon: 'exactfit' },
  reliable: { label: 'Reliable', icon: 'reliable' },
  durable: { label: 'Durable', icon: 'durable' },
  serviceable: { label: 'Serviceable', icon: 'serviceable' },
  available: { label: 'Available', icon: 'available' },
}
