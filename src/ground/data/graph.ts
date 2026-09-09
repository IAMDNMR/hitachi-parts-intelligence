import type { Confidence, Edge, GroundNode, NodeType, Provenance } from '../types/ground'

/**
 * THE GROUND — the model.
 *
 * A layered directed graph, not a tree. Nodes carry a `column`, the
 * architectural layer they belong to — which the layout no longer reads; see
 * the note on `column` in types/ground.ts for what it is still for and why it
 * was not deleted. Edges are declared separately from nodes, because the real thing is
 * a mesh: Service reaches into Parts, Machine Data reaches into both, the
 * dealer is arrived at from two directions, and several entities are written
 * by one system while being referenced by another. A parent/child tree
 * cannot express that, so this does not use one.
 *
 * COLUMNS
 * -------
 *    0  origin        Machine Sold, Customer, the sale, After-Sales
 *    3  pillar        Parts and Service branch here; Machine Data, Warranty
 *                     and Network are the same type but reached only by
 *                     drilling into the process that each one feeds
 *  4-12  process       the operational processes under each pillar
 *   13  system        ERP / WMS / TMS
 *   14  hub           EDI integration hubs
 *   15  thirdParty    external and satellite systems
 *   16  entity        the twelve data entities
 *   17  canonical     the canonical data model groups
 *   18  outcome       Uptime
 *
 * A process chain occupies a RUN of these numbers rather than one, so that a
 * sequence could read left to right. That was the intent when they were
 * authored and it is still the right intent — but no layout reads them
 * today, so the paragraph that used to stand here describing how columns
 * collapse at layout time was describing a mechanism that no longer exists.
 * The current layout ranks by relationship and draws a chain DOWN the page,
 * one step per row, which is why a process drill uses about a third of the
 * width of the screen. Reviving these numbers is the way out of that.
 *
 * PROGRESSIVE DISCLOSURE
 * ----------------------
 * Expansion is not declared here. Clicking a node shows what the node is
 * connected to, taken from `groundEdges` — see useGraphState. A hand-written
 * reveal list used to sit on each node beside those edges, and because it was
 * a tree laid over a mesh the two disagreed in fifty-two places.
 *
 * Within a process chain a step is revealed by the step BEFORE it, not by the
 * pillar at the head of the chain. Revealing the whole chain at once put nine
 * new columns on the canvas in a single click and forced the view down to a
 * scale at which nothing could be read.
 * So the first view is the business story end to end, and the enterprise
 * depth appears only as the user opens their way into it — which is what
 * keeps ~70 nodes readable.
 *
 * PROVENANCE
 * ----------
 * Two supplied reference diagrams are the source for everything from column
 * 13 rightwards: an EDI/ERP topology diagram, and a Parts canonical data
 * model table. Both carry their own uncertainty markers — a red "?", "not
 * routed", "no process", a "Proposed*" heading — and those are preserved
 * rather than resolved. Columns 0-12 come from this project's own data files
 * and the business journey the site already tells; where the brief named a
 * process the project holds no data for, it is marked accordingly.
 *
 * Nothing anywhere states a real customer, order, price, part number,
 * transaction or machine reading.
 */

const DIAGRAM_TOPOLOGY = 'reference diagram: Core ERP / EDI Hubs / 3rd Party Systems'
const DIAGRAM_CANONICAL = 'reference diagram: Parts ERP → WMS → TMS → Canonical Data Model'

const fromSite = (source: string): Provenance => ({ confidence: 'confirmed', source })
const fromTopology = (): Provenance => ({
  confidence: 'confirmed',
  sourceReference: DIAGRAM_TOPOLOGY,
})
const fromCanonical = (): Provenance => ({
  confidence: 'confirmed',
  sourceReference: DIAGRAM_CANONICAL,
})
const fromBrief = (source = 'named in the brief; no project data behind it'): Provenance => ({
  confidence: 'assumed',
  source,
})

/** The supplied diagram itself is unsure here — a "?", a note, a cropped box. */
const sourceUnsure = (source: string, sourceReference?: string): Provenance => ({
  confidence: 'source-unsure',
  source,
  sourceReference,
})

export const ORIGIN_ID = 'machine-sold'
/**
 * Where the page opens.
 *
 * The story starts at the machine being sold, but the subject of this page is
 * what happens afterwards. Opening on the origin showed three boxes — a sale,
 * a customer and a handover — with none of the ecosystem in sight. Opening on
 * After-Sales puts the spine above it and its five domains below it, so the
 * first thing on screen is the point everything expands from.
 */
export const OPENING_ID = 'after-sales'

export const groundNodes: GroundNode[] = [
  /* ============================================================ column 0 */
  {
    id: 'machine-sold',
    type: 'milestone',
    column: 0,
    label: 'Machine Sold',
    summary: 'Where every other relationship on this map begins.',
    role:
      'A machine leaving the factory is what creates a customer, an after-sales obligation, a parts demand and a service relationship. Everything below this point exists because this happened.',
    provenance: fromSite('business journey told by Sections 01-05'),
  },
  {
    id: 'customer',
    type: 'party',
    column: 0,
    label: 'Customer',
    summary: 'The party the machine and the support relationship belong to.',
    role:
      'The customer is also a data entity with a defined system of record — open Customer in the data layer to see where it is mastered.',
    provenance: fromSite('business journey'),
  },

  /* ============================================================ column 1 */
  {
    id: 'sales',
    type: 'stage',
    column: 0,
    label: 'Sales & Handover',
    summary: 'The machine is ordered, delivered and handed over.',
    role:
      'Handover is the hinge: responsibility transfers to the customer, and Hitachi’s role changes from selling the machine to keeping it working.',
    provenance: fromSite('business journey'),
  },
  {
    id: 'so-order',
    type: 'process',
    column: 0,
    label: 'Sales Order',
    summary: 'The machine is ordered for the customer.',
    provenance: fromSite('business journey'),
  },
  {
    id: 'so-delivery',
    type: 'process',
    column: 0,
    label: 'Delivery',
    summary: 'The machine reaches the working site.',
    provenance: fromSite('business journey'),
  },
  {
    id: 'so-handover',
    type: 'process',
    column: 0,
    label: 'Handover',
    summary: 'Responsibility transfers and the support obligation begins.',
    provenance: fromSite('business journey'),
  },

  /* ============================================================ column 2 */
  {
    id: 'after-sales',
    type: 'stage',
    column: 0,
    label: 'After-Sales',
    summary: 'Everything Hitachi does for the machine after it is sold.',
    role:
      'Everything below this point is after-sales, and it runs through two domains: Parts and Service. Machine Data, Warranty and the dealer network are not separate destinations — they are what feeds Parts and Service. Open either to find them: a monitoring reading raises a parts requirement, a warranty covers a repair, the dealer network is how both are actually delivered.',
    provenance: fromSite('project data: afterSalesStates.js'),
  },

  /* ============================================================ column 3 */
  {
    id: 'parts',
    type: 'pillar',
    column: 3,
    label: 'Parts',
    summary: 'Getting the right component to the machine that needs it.',
    role:
      'Open this to follow the parts process end to end, from the requirement being raised to the machine going back to work — and from there down into the systems that record each step.',
    provenance: fromSite('project data: partsCatalogue.js, journey.js'),
  },
  {
    id: 'service',
    type: 'pillar',
    column: 3,
    label: 'Service',
    summary: 'Expertise applied to the machine, on site or in the workshop.',
    role:
      'Service and Parts are not separate routes — a repair that needs a component crosses into the parts process and comes back.',
    provenance: fromSite('project data: serviceSteps.js'),
  },
  {
    id: 'machine-data',
    type: 'pillar',
    column: 3,
    label: 'Machine Data',
    summary: 'What the machine reports about itself as it works.',
    role:
      'The layer that makes the other four proactive rather than reactive: condition and monitoring data is what turns an unplanned failure into a planned intervention.',
    provenance: fromSite('project data: afterSalesStates.js, serviceSteps.js'),
  },
  {
    id: 'warranty',
    type: 'pillar',
    column: 3,
    label: 'Warranty',
    summary: 'The coverage under which parts and service work may be carried out.',
    role:
      'Warranty determines commercial treatment of a repair rather than its technical steps, which is why it connects to Service and Parts rather than sitting in their sequence.',
    detail: ['No warranty process data exists in this project — the connections shown are structural, not procedural'],
    provenance: fromBrief('pillar named in the brief; no warranty data in the project'),
  },
  {
    id: 'network',
    type: 'pillar',
    column: 3,
    label: 'Dealer / Service Network',
    summary: 'The physical network that delivers parts and service.',
    role:
      'Parts and service are strategy; the network is how either actually reaches a machine in the field.',
    provenance: fromSite('project data: ecosystemNodes.js — Network'),
  },

  /* ================================================ column 4 — parts flow */
  {
    id: 'p-requirement',
    type: 'process',
    column: 4,
    label: 'Parts Requirement',
    summary: 'A component is established as needed.',
    role: 'Reached from a service repair, from monitoring data, or from planned maintenance.',
    provenance: fromSite('project data: journey.js'),
  },
  {
    id: 'p-identification',
    type: 'process',
    column: 4,
    label: 'Part Identification',
    summary: 'Which exact component, for which machine configuration.',
    detail: ['Ten part families are catalogued in this project, from hydraulic cylinder to fuel injection pump'],
    provenance: fromSite('project data: partsCatalogue.js'),
  },
  {
    id: 'p-availability',
    type: 'process',
    column: 4,
    label: 'Parts Availability',
    summary: 'Whether the part is in stock, and where it is held.',
    provenance: fromSite('project data: journey.js'),
  },
  {
    id: 'p-ordering',
    type: 'process',
    column: 4,
    label: 'Parts Ordering',
    summary: 'A sales order is raised for the part.',
    role: 'The point at which the business process first becomes a record in an ERP system.',
    provenance: fromSite('project data: journey.js'),
  },
  {
    id: 'p-inventory',
    type: 'process',
    column: 4,
    label: 'Inventory',
    summary: 'Stock is allocated and drawn down.',
    provenance: fromSite('project data: journey.js'),
  },
  {
    id: 'p-shipment',
    type: 'process',
    column: 4,
    label: 'Shipment',
    summary: 'The part is picked, packed and moves.',
    provenance: fromSite('project data: journey.js'),
  },
  {
    id: 'p-goods-receipt',
    type: 'process',
    column: 4,
    label: 'Goods Receipt',
    summary: 'Arrival is confirmed against what was sent.',
    provenance: fromSite('project data: journey.js'),
  },
  {
    id: 'dealer',
    type: 'process',
    column: 4,
    label: 'Dealer',
    summary: 'The dealer holding the customer relationship and doing the work.',
    role:
      'Arrived at from several directions — the parts chain delivers to the dealer, a raised service need reaches the dealer alongside the technician it is assigned to, and the service network staffs it. The dealer, not a service centre, is the organisation the model hangs the work on.',
    provenance: fromSite('project data: ecosystemNodes.js'),
  },
  {
    id: 'p-installation',
    type: 'process',
    column: 4,
    label: 'Installation / Repair',
    summary: 'The part is fitted and the machine is made whole.',
    provenance: fromSite('project data: journey.js'),
  },

  /* ------------------------------------------- the core loop, closing back
     The parts chain ran one way — requirement to uptime — and stopped. Two
     things in the model said it should not.

     The canonical data model masters a RETURNS ORDER in D365 (see
     e-returns-order). It is the only entity in the data layer with a system
     of record and nothing upstream that creates one: an order type the
     client's own data model has, and their process diagram never says who
     raises. That is a finding about the supplied material, and the honest
     way to show it is to draw the process the entity implies and mark it
     inferred rather than to leave the entity floating.

     The site also already sells the other end of it. ecosystemNodes.js
     offers "Genuine, reman and value-line part ranges" — a remanufactured
     range cannot exist without cores coming back off machines.

     So the chain below is what has to be true for both of those to be true.
     None of it is drawn in either reference diagram, and every node says so.
     Nothing here states a rate, a yield, a core charge or a credit value. */
  {
    id: 'p-core-return',
    type: 'process',
    column: 4,
    label: 'Core Return',
    summary: 'The worn unit comes off the machine and goes back up the chain.',
    role:
      'The step that raises a returns order. It is the only process on this map inferred from an entity rather than the other way round — the canonical model has the order, so something must create it.',
    provenance: {
      confidence: 'inferred',
      source:
        'the canonical data model masters a Returns Order in IDMS D365; no supplied process says who raises one',
      sourceReference: DIAGRAM_CANONICAL,
    },
  },
  {
    id: 'p-core-assessment',
    type: 'process',
    column: 4,
    label: 'Core Assessment',
    summary: 'Whether the returned unit is worth rebuilding.',
    provenance: fromBrief('ordinary core-handling step; not in any supplied source'),
  },
  {
    id: 'p-reman',
    type: 'process',
    column: 4,
    label: 'Remanufacture',
    summary: 'An accepted core is rebuilt to specification and becomes sellable stock again.',
    role:
      'This is what makes the parts chain a loop rather than a line: what leaves as waste at the end of one cycle is the input to the next.',
    provenance: {
      confidence: 'inferred',
      source:
        'project data: ecosystemNodes.js offers a "reman" part range — a reman range implies cores are recovered and rebuilt',
    },
  },

  /* ============================================== column 4 — service flow */
  {
    id: 's-maintenance',
    type: 'process',
    column: 4,
    label: 'Maintenance',
    summary: 'Scheduled work that keeps the machine within specification.',
    provenance: fromSite('project data: serviceSteps.js — Maintain'),
  },
  {
    id: 's-preventive',
    type: 'process',
    column: 4,
    label: 'Preventive Maintenance',
    summary: 'Intervening before performance is compromised.',
    provenance: fromSite('project data: serviceSteps.js — Maintain'),
  },
  {
    id: 's-repair',
    type: 'process',
    column: 4,
    label: 'Repair',
    summary: 'Combining the right parts, expertise and service action.',
    role: 'Where service crosses into parts: a repair that needs a component raises a parts requirement.',
    provenance: fromSite('project data: serviceSteps.js — Repair'),
  },
  {
    id: 's-support',
    type: 'process',
    column: 4,
    label: 'Technical Support',
    summary: 'Expertise applied without necessarily attending the machine.',
    provenance: fromSite('project data: serviceSteps.js'),
  },
  {
    id: 's-need',
    type: 'process',
    column: 4,
    label: 'Service Need',
    summary: 'A machine issue or maintenance requirement is raised.',
    role:
      'The step this model was missing: where the journey actually starts. It is raised against the machine, not against a building, and it reaches both the dealer and the technician who is assigned — deciding where the work happens comes after this, not before it.',
    provenance: fromSite('project data: serviceSteps.js'),
  },
  {
    id: 's-technician',
    type: 'process',
    column: 4,
    label: 'Technician',
    summary: 'The dealer’s technician who diagnoses and carries out the work.',
    role:
      'Assigned by the dealer, not fielded by a building — the technician goes to the machine, or the machine comes to a dealer workshop, depending on what the job needs. Either way the technician, not a location, is the acting party.',
    provenance: fromSite('project data: ecosystemNodes.js — Service'),
  },

  /* ========================================= column 4 — machine data flow */
  {
    id: 'md-information',
    type: 'process',
    column: 4,
    label: 'Machine Information',
    summary: 'The machine’s identity, configuration and specification.',
    provenance: fromSite('project data: afterSalesStates.js'),
  },
  {
    id: 'md-status',
    type: 'process',
    column: 4,
    label: 'Machine Status',
    summary: 'What the machine currently reports about its own condition.',
    provenance: fromSite('project data: afterSalesStates.js'),
  },
  {
    id: 'md-history',
    type: 'process',
    column: 4,
    label: 'Service History',
    summary: 'Everything previously done to this machine.',
    role: 'History is what makes the next diagnosis faster than the last.',
    provenance: fromSite('project data: ecosystemNodes.js'),
  },
  {
    id: 'md-monitoring',
    type: 'process',
    column: 4,
    label: 'Monitoring',
    summary: 'Continuous observation rather than periodic inspection.',
    provenance: fromSite('project data: serviceSteps.js'),
  },
  {
    id: 'md-consite',
    type: 'process',
    column: 4,
    label: 'ConSite',
    summary: 'Hitachi’s monitoring and reporting service.',
    detail: ['Named in this project’s service section; its internal architecture is not supplied'],
    provenance: fromSite('project data: serviceSteps.js — ConSite'),
  },
  {
    id: 'md-global-eservice',
    type: 'process',
    column: 4,
    label: 'Global e-Service',
    summary: 'The platform machine information is reported through.',
    detail: ['Named in this project’s service section; its internal architecture is not supplied'],
    provenance: fromSite('project data: serviceSteps.js — Global e-Service'),
  },

  /* =============================================== column 4 — the network */
  {
    id: 'n-warehouses',
    type: 'process',
    column: 4,
    label: 'Parts Warehouses',
    summary: 'Where stock is physically held before it is needed.',
    provenance: fromSite('project data: ecosystemNodes.js — Network'),
  },
  {
    id: 'n-regional',
    type: 'process',
    column: 4,
    label: 'Regional Support',
    summary: 'Regional capability behind the local dealer.',
    provenance: fromBrief(),
  },

  /* ====================================================== column 5 — ERP */
  {
    id: 'sys-d365',
    type: 'system',
    column: 13,
    label: 'HCME D365 / IDMS',
    summary: 'System of record for parts orders; reference for customer, vendor and part.',
    role:
      'Where the parts business process becomes a record. Sales, purchase and returns orders are mastered here, and invoices originate here before SAP posts them.',
    detail: [
      'Sends account payables, receivables and general ledger transactions to the Domestic Hub – Dynamics',
      'Connects to SAP ECC — the relationship is drawn in the source diagram but that segment carries no flow label',
      'Sends customer change, vendor change and payables/receivables directly to HCME Annata',
      '"DIP Machine" appears on that flow marked with a question mark in the source',
    ],
    provenance: fromTopology(),
  },
  {
    id: 'sys-sap',
    type: 'system',
    column: 13,
    label: 'SAP ECC',
    summary: 'System of record for customer and vendor masters, and for finance.',
    role:
      'Masters flow from SAP outward to every other system. SAP is also where the general ledger and payments live, and where invoices are posted.',
    detail: [
      'Sends payables, receivables and general ledger transactions to the Banks & Concur hub',
      'A second line into that same hub is marked only with a question mark in the source diagram',
      'Sends adjust, cancel, clearing, receipt, shipment and stock movement transactions to the Deloitte Trackon Trade hub',
      'The source also flags on that path: equipment change has no process, plus a stock spreadsheet, stock movement errors and adjustment errors',
      'Its line to the Annata Azure hub is marked with a question mark in the source diagram',
    ],
    provenance: fromTopology(),
  },
  {
    id: 'sys-neovia',
    type: 'system',
    column: 13,
    label: 'Neovia — WMS / TMS',
    summary: 'Warehouse and transport execution.',
    role:
      'The execution layer for physical movement. Shipment is planned in D365 but executed here; goods receipt and stock movement are recorded here outright.',
    detail: [
      'System of record for goods receipt and stock movement.',
      'Executes shipment; D365 plans it.',
      'The only third-party integration named against an entity in the data model: Customer.',
    ],
    provenance: fromCanonical(),
  },
  {
    id: 'sys-annata',
    type: 'system',
    column: 13,
    label: 'HCME Annata (Dealer)',
    summary: 'The dealer-facing system.',
    detail: [
      'Built on Dynamics 365, so this is the customer- and dealer-facing system in this landscape. Where a CRM is asked for, this is the nearest thing the supplied architecture contains — no separate CRM appears in either source diagram.',
      'Receives customer change, vendor change and payables/receivables through the Every Angle hub. The topology diagram shows that flow leaving the hub, not D365.',
      'Exchanges stock and invoice data through the Azure Blob hub',
    ],
    provenance: fromTopology(),
  },

  /* ===================================================== column 6 — hubs */
  {
    id: 'hub-dynamics',
    type: 'hub',
    column: 13,
    label: 'Domestic Hub — Dynamics',
    summary: 'Routes finance transactions from D365 / IDMS to Deutsche Bank.',
    detail: [
      'Flagged in the source as NOT ROUTED: Deutsche Bank dbdi report files, Deutsche Bank EY files',
      'Flagged in the source with a question mark: Deutsche Bank XML S4 HANA',
    ],
    provenance: fromTopology(),
  },
  {
    id: 'hub-banks-concur',
    type: 'hub',
    column: 13,
    label: 'Hub — Banks & Concur',
    summary: 'Routes finance transactions from SAP ECC to Concur.',
    detail: ['One of its inbound lines is marked only with a question mark in the source diagram'],
    provenance: fromTopology(),
  },
  {
    id: 'hub-trackon',
    type: 'hub',
    column: 13,
    label: 'Hub — Deloitte Trackon Trade',
    summary: 'Routes stock and adjustment transactions from SAP ECC to Trackon Trade.',
    detail: [
      'The source diagram flags equipment change as having no process, alongside a stock spreadsheet, stock movement errors and adjustment errors',
    ],
    provenance: fromTopology(),
  },
  {
    id: 'hub-annata-azure',
    type: 'hub',
    column: 13,
    label: 'Hub — Annata Azure',
    summary: 'Routes inventory and material data out to Every Angle.',
    detail: ['Its inbound line from SAP ECC is marked with a question mark in the source diagram'],
    provenance: fromTopology(),
  },
  {
    id: 'hub-every-angle',
    type: 'hub',
    column: 13,
    label: 'Hub — Every Angle',
    summary: 'Drawn as a hub in the source, with no flow of its own labelled.',
    detail: [
      'The source draws no input to this hub. Customer and vendor changes have to originate where those masters live, which the data model states is SAP, so that is where the inbound edge has been put -- as an inference, not as something the diagram shows.',
      'The source diagram shows this hub without a distinctly labelled inbound or outbound flow',
      'The Every Angle data flow that is drawn originates from the Annata Azure hub',
    ],
    provenance: {
      confidence: 'not-supplied',
      sourceReference: DIAGRAM_TOPOLOGY,
      source: 'no distinct flow shown for this hub',
    },
  },
  {
    id: 'hub-azure-blob',
    type: 'hub',
    column: 13,
    label: 'Hub — Azure Blob',
    summary: 'Carries stock and invoice data between Annata and Delvator Kiesel.',
    detail: [
      'The source draws no input to this hub either. Stock and invoice originate where the data model puts them, and it gives the origin of an invoice as IDMS D365, so that is where the inbound edge has been put -- as an inference.',
      'Carries stock and invoice.',
      'Feeds two destinations from one hub: HCME Annata and Delvator Kiesel.',
    ],
    provenance: fromTopology(),
  },

  /* ============================================== column 7 — third party */
  {
    id: 'tp-deutsche-bank',
    type: 'third-party',
    column: 13,
    label: 'Deutsche Bank',
    summary: 'Banking counterparty for inbound and outbound files.',
    detail: ['Two named file flows are marked not routed, and one is marked with a question mark, in the source'],
    provenance: fromTopology(),
  },
  {
    id: 'tp-concur',
    type: 'third-party',
    column: 13,
    label: 'Concur',
    summary: 'Expense system.',
    detail: [
      'Encrypted expense.',
      'HCME Concur totals, vanilla.',
      'HCME decrypted financial extract.',
      'HCME cash payments.',
      'HCME credit payments.',
    ],
    provenance: fromTopology(),
  },
  {
    id: 'tp-trackon',
    type: 'third-party',
    column: 13,
    label: 'Trackon Trade',
    summary: 'Trade and stock transaction counterparty.',
    detail: [
      'Adjust, cancel, clearing, receipt, shipment and stock movement transactions.',
      'Marked in red in the source: equipment change has no process.',
      'Stock spreadsheet.',
      'Stock movement errors.',
      'Adjustment errors.',
    ],
    provenance: fromTopology(),
  },
  {
    id: 'tp-every-angle',
    type: 'third-party',
    column: 13,
    label: 'Every Angle',
    summary: 'Analytics over inventory, purchasing and material data.',
    detail: [
      'Oasis file.',
      'Data1 pegging data, Data2 open PO lines, Data3 inventory transactions.',
      'Data4 parts supplier data, Data5 parts inventory.',
      'Material files and material BOM files.',
      'The whole of this list is red in the source diagram.',
    ],
    provenance: fromTopology(),
  },
  {
    id: 'tp-delvator',
    type: 'third-party',
    column: 13,
    label: 'Delvator Kiesel',
    summary: 'Dealer-side counterparty for stock and invoice data.',
    detail: [
      'Stock.',
      'Invoice.',
    ],
    provenance: fromTopology(),
  },

  /* ================================================== column 8 — entities
     `facts` are the source table's own cells. A cell the table left blank is
     kept blank rather than filled in. */
  {
    id: 'e-customer',
    type: 'entity',
    column: 16,
    label: 'Customer',
    summary: 'The party a machine is sold to and supported for.',
    facts: [
      { label: 'System of Record', value: 'SAP — masters flow SAP → everywhere' },
      { label: 'System of Reference', value: 'IDMS D365, D365 Annata' },
      { label: '3rd Party Integration', value: 'Neovia' },
    ],
    provenance: fromCanonical(),
  },
  {
    id: 'e-vendor',
    type: 'entity',
    column: 16,
    label: 'Vendor',
    summary: 'A supplier the business buys from.',
    facts: [
      { label: 'System of Record', value: 'SAP — masters flow SAP → everywhere' },
      { label: 'System of Reference', value: 'IDMS D365, D365 Annata' },
      { label: '3rd Party Integration' },
    ],
    provenance: fromCanonical(),
  },
  {
    id: 'e-part',
    type: 'entity',
    column: 16,
    label: 'Part',
    summary: 'The component being identified, ordered and fitted.',
    facts: [
      { label: 'System of Record', value: 'GOM globally; IDMS D365 for HCME' },
      { label: 'System of Reference', value: 'IDMS D365, Annata' },
      { label: '3rd Party Integration' },
    ],
    provenance: fromCanonical(),
  },
  {
    id: 'e-sales-order',
    type: 'entity',
    column: 16,
    label: 'Sales Order',
    summary: 'An order raised for a customer.',
    facts: [
      { label: 'System of Record', value: 'IDMS D365' },
      { label: 'System of Reference' },
      { label: '3rd Party Integration' },
    ],
    provenance: fromCanonical(),
  },
  {
    id: 'e-purchase-order',
    type: 'entity',
    column: 16,
    label: 'Purchase Order',
    summary: 'An order raised to a vendor.',
    facts: [
      { label: 'System of Record', value: 'IDMS D365' },
      { label: 'System of Reference', value: 'SAP' },
      { label: '3rd Party Integration' },
    ],
    provenance: fromCanonical(),
  },
  {
    id: 'e-returns-order',
    type: 'entity',
    column: 16,
    label: 'Returns Order',
    summary: 'A part being returned.',
    facts: [
      { label: 'System of Record', value: 'IDMS D365' },
      { label: 'System of Reference' },
      { label: '3rd Party Integration' },
    ],
    provenance: fromCanonical(),
  },
  {
    id: 'e-shipment',
    type: 'entity',
    column: 16,
    label: 'Shipment',
    summary: 'Parts in transit.',
    facts: [
      { label: 'System of Record', value: 'Neovia for execution; D365 for the plan' },
      { label: 'System of Reference' },
      { label: '3rd Party Integration' },
    ],
    provenance: fromCanonical(),
  },
  {
    id: 'e-goods-receipt',
    type: 'entity',
    column: 16,
    label: 'Goods Receipt',
    summary: 'Confirmation that a shipment arrived.',
    facts: [
      { label: 'System of Record', value: 'Neovia' },
      { label: 'System of Reference' },
      { label: '3rd Party Integration' },
    ],
    provenance: fromCanonical(),
  },
  {
    id: 'e-stock-movement',
    type: 'entity',
    column: 16,
    label: 'Stock Movement',
    summary: 'A change in where or how much stock is held.',
    facts: [
      { label: 'System of Record', value: 'Neovia' },
      { label: 'System of Reference' },
      { label: '3rd Party Integration' },
    ],
    provenance: fromCanonical(),
  },
  {
    id: 'e-invoice',
    type: 'entity',
    column: 16,
    label: 'Invoice',
    summary: 'A bill raised for parts or service.',
    facts: [
      { label: 'System of Record', value: 'SAP for posting; D365 for origin' },
      { label: 'System of Reference' },
      { label: '3rd Party Integration' },
    ],
    provenance: fromCanonical(),
  },
  {
    id: 'e-gl-journal',
    type: 'entity',
    column: 16,
    label: 'GL Journal',
    summary: 'A general ledger posting.',
    facts: [
      { label: 'System of Record', value: 'SAP' },
      { label: 'System of Reference' },
      { label: '3rd Party Integration' },
    ],
    provenance: fromCanonical(),
  },
  {
    id: 'e-payment',
    type: 'entity',
    column: 16,
    label: 'Payment',
    summary: 'Money moving to settle an invoice.',
    facts: [
      { label: 'System of Record', value: 'SAP / banks' },
      { label: 'System of Reference' },
      { label: '3rd Party Integration' },
    ],
    detail: [
      'Grouped under Finance here alongside invoice and GL journal. The canonical diagram supplied is cropped at that edge, so the grouping follows its system of record rather than a box that can be read.',
    ],
    provenance: fromCanonical(),
  },

  /* ================================================= column 9 — canonical */
  {
    id: 'cdm-party',
    type: 'canonical',
    column: 17,
    label: 'Party',
    summary: 'Customer and Vendor.',
    provenance: fromCanonical(),
  },
  {
    id: 'cdm-product',
    type: 'canonical',
    column: 17,
    label: 'Product',
    summary: 'Part.',
    provenance: fromCanonical(),
  },
  {
    id: 'cdm-orders',
    type: 'canonical',
    column: 17,
    label: 'Orders',
    summary: 'Sales, purchase and returns orders.',
    detail: ['Sales orders are shown in the source as flowing GOM → IDMS'],
    provenance: fromCanonical(),
  },
  {
    id: 'cdm-logistics',
    type: 'canonical',
    column: 17,
    label: 'Logistics',
    summary: 'Shipment, goods receipt and stock movement.',
    detail: [
      'This group’s own box is cut off in the supplied image, so its label is inferred; the three entities under it are fully sourced from the table',
    ],
    provenance: sourceUnsure(
      'this group box is cropped out of the supplied image',
      DIAGRAM_CANONICAL,
    ),
  },
  {
    id: 'cdm-finance',
    type: 'canonical',
    column: 17,
    label: 'Finance',
    summary: 'Invoice, GL journal and payment.',
    provenance: fromCanonical(),
  },

  /* ================================================== column 10 — outcome */
  {
    id: 'uptime',
    type: 'milestone',
    column: 18,
    label: 'Uptime',
    summary: 'The machine working. The point of everything above it.',
    role:
      'Uptime is not a system or a process — it is the outcome the whole architecture exists to produce. Parts, service, machine data and the dealer network all resolve here.',
    provenance: fromSite('business journey — Section 05'),
  },
  /* ================================================================ warranty
     The brief asks Warranty to open like the other pillars. No supplied
     diagram covers it, so these are the ordinary stages of a claim, marked
     assumed rather than presented as Hitachi's actual process. */
  {
    id: 'w-registration',
    type: 'process',
    column: 4,
    label: 'Warranty Registration',
    summary: 'Cover is recorded against the machine at handover.',
    provenance: fromBrief('ordinary claim stage; not in any supplied source'),
  },
  {
    id: 'w-claim',
    type: 'process',
    column: 4,
    label: 'Warranty Claim',
    summary: 'A failure within cover is raised, usually by the dealer.',
    provenance: fromBrief('ordinary claim stage; not in any supplied source'),
  },
  {
    id: 'w-assessment',
    type: 'process',
    column: 4,
    label: 'Claim Assessment',
    summary: 'The claim is judged against the terms of cover.',
    provenance: fromBrief('ordinary claim stage; not in any supplied source'),
  },
  {
    id: 'w-settlement',
    type: 'process',
    column: 4,
    label: 'Settlement',
    summary: 'An accepted claim is credited, and its parts and labour accounted for.',
    provenance: fromBrief('ordinary claim stage; not in any supplied source'),
  },
]

/* --------------------------------------------------------------- edges */

const e = (
  from: string,
  to: string,
  label?: string,
  kind: Edge['kind'] = 'flow',
  confidence: Edge['confidence'] = 'confirmed',
): Edge => ({ from, to, label, kind, confidence })

export const groundEdges: Edge[] = [
  /* the spine */
  e('machine-sold', 'customer', 'sold to'),
  e('machine-sold', 'sales'),
  e('customer', 'sales'),
  e('sales', 'so-order'),
  e('so-order', 'so-delivery'),
  e('so-delivery', 'so-handover'),
  e('so-handover', 'after-sales'),
  e('sales', 'after-sales'),

  /* The two domains. Machine Data, Warranty and the dealer network used to
     branch here too, as three more peer pillars — which put "data the
     machine reports about itself" and "the coverage a repair is billed
     under" visually level with "parts" and "service", as if a client chose
     between five equally-weighted categories.

     They are not categories a client chooses between; they are inputs. A
     monitoring reading raises a parts requirement (md-monitoring feeds
     p-requirement below), a warranty covers a repair and a parts order
     (warranty feeds s-repair and p-ordering), and the dealer network is who
     actually carries out both. Every one of those edges already existed —
     removing the direct branch from After-Sales does not remove the nodes,
     it removes the second, competing way into them. They are still on the
     canvas, still fully explorable, still carry every field they always
     have; they now arrive as what they are — something Parts or Service
     reaches into — rather than as a sixth thing sitting beside them. */
  e('after-sales', 'parts'),
  e('after-sales', 'service'),

  /* parts process */
  e('parts', 'p-requirement'),
  e('p-requirement', 'p-identification'),
  e('p-identification', 'p-availability'),
  e('p-availability', 'p-ordering'),
  e('p-ordering', 'p-inventory'),
  e('p-inventory', 'p-shipment'),
  e('p-shipment', 'p-goods-receipt'),
  e('p-goods-receipt', 'dealer'),
  e('dealer', 'p-installation'),
  e('p-installation', 'uptime'),

  /* The core loop — see the nodes above for what each one claims.

     `p-reman → p-inventory` is the FIRST CYCLE in this model. Everything
     else is a strict DAG, and layout.ts ranks by topological sort with a
     fallback to index order for exactly this case — a fallback that had
     never run, because until now nothing could reach it.

     Two things were checked before this edge was committed rather than
     assumed:

     1. It is not reachable through the interface. rankNodes only sees the
        VISIBLE subgraph, and the visible set is six route nodes plus the
        selection's neighbours. This loop is eight nodes, so no selection
        puts all of it on screen at once — walking the whole chain, the
        deepest view holds seven of the eight and ranks cleanly.
     2. It is harmless if it ever is. Forcing all eight into one visible set
        places 8 of 8 with no overlapping boxes, no non-finite coordinates
        and no malformed connector paths; it degrades to a one-wide ribbon,
        which is ugly and correct. The whole 75-node model forced onto one
        canvas behaves the same way.

     So raising ROUTE_ON_CANVAS later is a legibility decision, not a
     correctness risk. */
  e('p-installation', 'p-core-return', 'core removed', 'flow', 'inferred'),
  e('p-core-return', 'p-core-assessment', undefined, 'flow', 'assumed'),
  e('p-core-assessment', 'p-reman', 'rebuildable', 'flow', 'assumed'),
  e('p-reman', 'p-inventory', 'back to sellable stock', 'flow', 'inferred'),

  /* service process */
  e('service', 's-need'),
  e('s-need', 'dealer', 'raised to'),
  e('s-need', 's-technician', 'assigned to'),
  e('service', 's-maintenance'),
  e('service', 's-support'),
  e('s-maintenance', 's-preventive'),
  e('s-maintenance', 's-repair'),
  e('s-support', 's-repair'),
  e('s-technician', 's-repair', 'carries out'),
  e('s-repair', 'p-requirement', 'parts required'),
  e('s-preventive', 'uptime'),
  e('dealer', 'uptime'),

  /* machine data */
  e('machine-data', 'md-information'),
  e('md-information', 'md-status'),
  e('md-information', 'md-history'),
  e('md-status', 'md-monitoring'),
  e('md-monitoring', 'md-global-eservice'),
  e('md-global-eservice', 'md-consite', undefined, 'flow', 'inferred'),
  e('md-consite', 's-maintenance', 'informs service'),
  e('md-history', 's-repair', 'prior work'),
  e('md-monitoring', 'p-requirement', 'predicted demand'),
  e('md-consite', 'uptime'),

  /* warranty and network */
  e('warranty', 's-repair', 'coverage', 'flow', 'assumed'),
  e('warranty', 'p-ordering', 'coverage', 'flow', 'assumed'),
  e('network', 'dealer'),
  e('network', 's-technician'),
  e('network', 'n-warehouses'),
  e('network', 'n-regional'),
  e('n-warehouses', 'p-inventory', 'stock held'),
  e('n-regional', 'dealer', 'regional capability', 'flow', 'assumed'),

  /* process → system */
  e('p-identification', 'sys-d365', 'part master', 'system'),
  e('p-availability', 'sys-d365', 'stock enquiry', 'system'),
  e('p-ordering', 'sys-d365', 'sales order', 'system'),
  e('p-inventory', 'sys-neovia', 'stock movement', 'system'),
  e('p-shipment', 'sys-neovia', 'shipment', 'system'),
  e('p-goods-receipt', 'sys-neovia', 'goods receipt', 'system'),
  /* The edge that stops Returns Order being an orphan. The entity was
     already wired to D365 as its system of record; nothing reached D365
     from the process side to produce one. */
  e('p-core-return', 'sys-d365', 'returns order', 'system', 'inferred'),
  e('dealer', 'sys-annata', 'dealer information', 'system'),
  e('n-warehouses', 'sys-neovia', 'warehouse execution', 'system'),

  /* system ↔ system */
  e('sys-d365', 'sys-sap', 'no flow label in source', 'system', 'source-unsure'),
  e('hub-every-angle', 'sys-annata', 'customer change · vendor change · payables · receivables', 'system'),

  /* system → hub */
  e('sys-d365', 'hub-dynamics', 'payables · receivables · GL transactions', 'integration'),
  e('sys-sap', 'hub-banks-concur', 'payables · receivables · GL transactions', 'integration'),
  e('sys-sap', 'hub-trackon', 'adjust · cancel · clearing · receipt · shipment · stock movement', 'integration'),
  e('sys-sap', 'hub-annata-azure', 'marked "?" in source', 'integration', 'source-unsure'),
  e('sys-sap', 'hub-every-angle', 'customer · vendor masters', 'integration', 'inferred'),
  e('sys-d365', 'hub-azure-blob', 'stock · invoice', 'integration', 'inferred'),
  e('hub-azure-blob', 'sys-annata', 'stock · invoice', 'integration'),

  /* hub → third party */
  e('hub-dynamics', 'tp-deutsche-bank', 'inbound · outbound', 'integration'),
  e('hub-banks-concur', 'tp-concur', 'expense · totals · financial extract · cash & credit payments', 'integration'),
  e('hub-trackon', 'tp-trackon', 'stock movement · adjustment transactions', 'integration'),
  e('hub-annata-azure', 'tp-every-angle', 'inventory · open PO lines · parts supplier · material BOM', 'integration'),
  e('hub-azure-blob', 'tp-delvator', 'stock · invoice', 'integration'),

  /* system → entity (system of record) */
  e('sys-sap', 'e-customer', 'system of record', 'data'),
  e('sys-sap', 'e-vendor', 'system of record', 'data'),
  e('sys-d365', 'e-part', 'system of record (HCME)', 'data'),
  e('sys-d365', 'e-sales-order', 'system of record', 'data'),
  e('sys-d365', 'e-purchase-order', 'system of record', 'data'),
  e('sys-d365', 'e-returns-order', 'system of record', 'data'),
  e('sys-neovia', 'e-shipment', 'execution', 'data'),
  e('sys-neovia', 'e-goods-receipt', 'system of record', 'data'),
  e('sys-neovia', 'e-stock-movement', 'system of record', 'data'),
  e('sys-sap', 'e-invoice', 'posting', 'data'),
  e('sys-d365', 'e-invoice', 'origin', 'data'),
  e('sys-sap', 'e-gl-journal', 'system of record', 'data'),
  e('sys-sap', 'e-payment', 'system of record', 'data'),

  /* entity → canonical model */
  e('e-customer', 'cdm-party', undefined, 'data'),
  e('e-vendor', 'cdm-party', undefined, 'data'),
  e('e-part', 'cdm-product', undefined, 'data'),
  e('e-sales-order', 'cdm-orders', undefined, 'data'),
  e('e-purchase-order', 'cdm-orders', undefined, 'data'),
  e('e-returns-order', 'cdm-orders', undefined, 'data'),
  e('e-shipment', 'cdm-logistics', undefined, 'data'),
  e('e-goods-receipt', 'cdm-logistics', undefined, 'data'),
  e('e-stock-movement', 'cdm-logistics', undefined, 'data'),
  e('e-invoice', 'cdm-finance', undefined, 'data'),
  e('e-gl-journal', 'cdm-finance', undefined, 'data'),
  e('e-payment', 'cdm-finance', undefined, 'data'),
  /* service reaches the dealer system it is recorded in */
  e('s-repair', 'sys-annata', 'job recorded in', 'system', 'assumed'),




  /* warranty, as a claim */
  e('warranty', 'w-registration', undefined, 'flow', 'assumed'),
  e('w-registration', 'w-claim', undefined, 'flow', 'assumed'),
  e('w-claim', 'w-assessment', undefined, 'flow', 'assumed'),
  e('w-assessment', 'w-settlement', undefined, 'flow', 'assumed'),
  e('dealer', 'w-claim', 'raises', 'flow', 'assumed'),
  e('w-settlement', 'e-invoice', 'credited via', 'data', 'assumed'),

]

/** Column index → the label shown above that band of the canvas. */
/**
 * Headings for the architectural bands.
 *
 * Columns 4 to 12 are one band, not nine: the operational processes run left
 * to right across all of them, so they share a heading and the canvas draws
 * it once over the whole span. Naming only the first left the other eight
 * rendering an empty heading above a bare rule.
 */
/** What a node is, in words, for the detail card. */
export const NODE_TYPE_LABELS: Readonly<Record<NodeType, string>> = {
  milestone: 'Milestone',
  party: 'Party',
  stage: 'Business Stage',
  pillar: 'After-Sales Domain',
  process: 'Business Process',
  system: 'Enterprise System',
  hub: 'Integration Hub',
  'third-party': 'Third-Party System',
  entity: 'Data Entity',
  canonical: 'Canonical Model',
}

/**
 * How sure the model is about a node or a line, in words.
 *
 * The vocabulary was previously carried only by the dash pattern of a
 * connector, which cannot be read without a key. These are the words the
 * legend and the on-node flags both use, so one phrase describes each state
 * wherever it appears.
 */
export const CONFIDENCE_LABELS: Readonly<Record<Confidence, string>> = {
  confirmed: 'Confirmed by supplied material',
  'source-unsure': 'The source itself marks this uncertain',
  inferred: 'Inferred from something stated',
  assumed: 'Assumed — nothing behind it',
  demo: 'Illustrative only',
  'not-supplied': 'Not supplied',
}
