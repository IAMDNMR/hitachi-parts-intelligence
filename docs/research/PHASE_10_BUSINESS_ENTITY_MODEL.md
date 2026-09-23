# Parts & Service — Business Entities and How They Connect

Scope: HCME Europe Parts & Service only, seen from a Parts Intelligence perspective.
This page describes business meaning only. It does not describe how anything is built.

---

## The six core entities at a glance

```
                    Supplier
                       │ supplies
                       ▼
  Purchase Order ──buys──►  Product / Part  ◄──contains── Sales Order ◄──places── Customer
        ▲                     ▲        │                                            │
        │ places              │ is part of                                          │ buys
     Company (HCME)           │        ▼                                            ▼
                             BOM ──defines structure of──► Machine ◄──owns / operates──┘
```

---

## 1. Product / Part

**What it represents**
A genuine Hitachi part that keeps a construction machine working. Examples include a hydraulic
filter, a battery, a track roller, a main hydraulic pump or a litre of genuine hydraulic oil.
It is the thing customers need, dealers sell, and the company buys and stocks.

**Important business information**
- Part number and part name
- Category and sub-category, for example Hydraulics / Control Valve or Undercarriage / Track Roller
- Which assembly of the machine it belongs to, for example the hydraulic system or the undercarriage
- Type of part: wear part, service part, consumable, or remanufactured major component
- Which machine models it fits
- Whether it has a newer replacement (supersession) or an approved alternative
- Where the information came from and how trustworthy it is

**Connects to**

| Relationship | Other entity | Business meaning |
|---|---|---|
| Part → **fits** → Machine | Machine | The part can be installed on these machine models. |
| Part → **is listed in** → BOM | BOM | The part is one line in a machine's parts structure, with a quantity. |
| Part → **is supplied by** → Supplier | Supplier | The company or companies that make or provide the part. |
| Part → **is ordered on** → Sales Order | Sales Order | Customers or dealers have asked for it. |
| Part → **is bought on** → Purchase Order | Purchase Order | The company has bought it to restock. |
| Part → **can be replaced by** → Part | Part | An alternative or superseding part number. |
| Part → **must meet** → Compliance requirement | Compliance | Regulations and standards the part has to satisfy in Europe. |

**Why it matters for Parts Intelligence**
The part is the centre of almost every question: "What is it?", "Does it fit my machine?",
"Where can I get it?", "What happens if it runs out?". Every other entity is reached through it.

---

## 2. BOM (Bill of Materials)

**What it represents**
The parts structure of a machine: which assemblies the machine is built from, which parts sit in
each assembly, and how many of each part is used. For example, a ZX210-7 excavator has an
undercarriage assembly that contains track rollers, carrier rollers and drive sprockets, each in
a fixed quantity.

**Important business information**
- The machine model the structure belongs to
- The assemblies, for example Engine, Hydraulic system, Undercarriage, Electrical system or Cab
- The parts within each assembly
- Quantity of each part per machine
- How critical each assembly is to keeping the machine running

**Connects to**

| Relationship | Other entity | Business meaning |
|---|---|---|
| BOM → **defines the structure of** → Machine | Machine | Tells you what the machine is made of. |
| BOM → **is made of** → Part | Part | Each line of the BOM is one part and its quantity. |
| Assembly → **carries** → Compliance requirement | Compliance | Requirements that apply to an assembly also apply to the parts inside it. |

**Why it matters for Parts Intelligence**
The BOM turns a single part into a business impact. For example: "this part is used 3 times in the
hydraulic system of 4 machine models". That tells you how many machines stop if the part is
unavailable and which assemblies are critical. It also shows which compliance requirements a part
inherits from the assembly it sits in. This is what the **Impact** view is built on: affected
machines, total BOM quantity, critical paths and affected assemblies.

---

## 3. Customer

**What it represents**
The machine owner or operator who needs parts, such as a construction contractor, a rental
company, a quarry or a demolition firm. In Europe the customer normally deals with HCME through a
local Hitachi dealer.

**Important business information**
- Name, company and contact details
- Country and location
- The machines they own or operate
- Their preferred or nearest dealer
- Their order history

**Connects to**

| Relationship | Other entity | Business meaning |
|---|---|---|
| Customer → **places** → Sales Order | Sales Order | The customer asks for parts. |
| Customer → **buys** → Part | Part | Through a sales order, usually via a dealer. |
| Customer → **owns / operates** → Machine | Machine | Tells you which parts the customer will need. |
| Customer → **is served by** → Dealer | Dealer | The dealer that sells, delivers and services for this customer. |

**Why it matters for Parts Intelligence**
The customer gives a question its context. "Which dealer is nearest to me?" and "Will this part
fit my machine?" can only be answered when you know who is asking, where they are and what they
run.

---

## 4. Supplier

**What it represents**
The company that makes or provides a part to HCME. Suppliers include Hitachi's own factories,
component makers for engines, pumps and batteries, and fluid producers.

**Important business information**
- Supplier name, country and region
- Which parts it supplies, and what share of each part's volume
- Supplier tier (direct supplier, or a supplier's supplier)
- Whether a part can be bought from more than one supplier (dual-source) or only one (sole source)
- Reliability and risk indicators

**Connects to**

| Relationship | Other entity | Business meaning |
|---|---|---|
| Supplier → **supplies** → Part | Part | The supplier provides this part, with a share of volume. |
| Supplier → **receives** → Purchase Order | Purchase Order | The company orders from the supplier. |
| Supplier → **delivers to** → Depot | Depot | Stock arrives at the European parts centre. |

**Why it matters for Parts Intelligence**
Supplier links show where the risk is. If a part has one supplier and that supplier fails, every
machine that uses the part is at risk. The link answers "Is this part single-source?", "How
dependent are we on this supplier across all parts?" and "Is there a second source?". This is what
the **Supplier Risk** view shows.

---

## 5. Sales Order

**What it represents**
A request from a customer or dealer to buy parts: the demand side of the business.

**Important business information**
- Order number and date
- Who ordered it (customer and/or dealer)
- Which parts, and how many of each
- Delivery destination (usually a dealer branch)
- Status: created, accepted, allocated, shipped, delivered or closed
- Fulfilment choice (where the stock comes from and how it travels)
- Linked shipment and, where relevant, the service job it supports

**Connects to**

| Relationship | Other entity | Business meaning |
|---|---|---|
| Customer → **places** → Sales Order | Customer | Who is buying. |
| Sales Order → **contains** → Part | Part | What is being bought, and how many. |
| Sales Order → **is delivered to** → Dealer | Dealer | Where it goes. |
| Sales Order → **is fulfilled from** → Depot | Depot | Where the stock is picked. |
| Sales Order → **ships as** → Shipment | Shipment | How it physically travels. |
| Sales Order → **supports** → Service Job | Service Job | The repair or maintenance the part is for. |

**Why it matters for Parts Intelligence**
Sales orders show real demand and answer "Where is my order?". They also show the business effect
of a shortage: if a part is short, the open sales orders for it are the orders at risk.

---

## 6. Purchase Order

**What it represents**
A request from the company (HCME) to a supplier to buy parts: the supply side of the business.
It is how the European parts centre is restocked.

**Important business information**
- Purchase order number and date
- Supplier
- Which parts, and how many
- Expected delivery date to the depot
- Status: placed, confirmed, in transit or received

**Connects to**

| Relationship | Other entity | Business meaning |
|---|---|---|
| Company → **places** → Purchase Order | Company (HCME) | The company is the buyer. |
| Purchase Order → **buys** → Part | Part | What is being restocked. |
| Purchase Order → **is sent to** → Supplier | Supplier | Who is supplying it. |
| Purchase Order → **delivers into** → Depot | Depot | Where the stock will land. |

**Why it matters for Parts Intelligence**
Purchase orders show incoming supply. When a part is short, open purchase orders answer "When will
it be back?". A part with no open purchase order and a sole supplier is a disruption waiting to
happen.

---

## Supporting entities (needed to make the six meaningful)

| Entity | What it is | Key connections |
|---|---|---|
| **Machine** | A Hitachi machine model, for example a ZX210-7 excavator or a ZW180-7 wheel loader | Part fits Machine · BOM defines Machine · Customer operates Machine |
| **Dealer** | An authorised Hitachi dealer branch in Europe | Serves Customer · receives Sales Order deliveries · performs Service Jobs |
| **Depot** | The European parts centre (Oosterhout, NL) | Holds stock of Parts · fulfils Sales Orders · receives Purchase Orders |
| **Company (HCME)** | Hitachi Construction Machinery Europe | Places Purchase Orders · sells to Dealers and Customers |
| **Compliance requirement** | A European regulation or standard, for example CE marking, REACH, RoHS, the EU Battery Regulation or EU Stage V | Applies to Parts directly, or is inherited through the Assembly they sit in |

---

## All relationships in plain terms

```
Product/Part      → fits                    → Machine
Product/Part      → is made of              → Parts/Components (BOM)
BOM               → defines                 → Product/Part structure (Machine → Assembly → Part, with quantity)
Product/Part      → supplied by             → Supplier
Product/Part      → can be replaced by      → Alternative Part
Product/Part      → must meet               → Compliance requirement
Assembly          → passes on               → Compliance requirement (to every Part inside it)
Customer          → buys                    → Product/Part
Customer          → places                  → Sales Order
Customer          → operates                → Machine
Customer          → is served by            → Dealer
Sales Order       → contains                → Product/Part
Sales Order       → is delivered to         → Dealer
Sales Order       → is fulfilled from       → Depot
Sales Order       → ships as                → Shipment
Company           → places                  → Purchase Order
Purchase Order    → buys                    → Product/Part
Purchase Order    → is sent to              → Supplier
Purchase Order    → restocks                → Depot
Supplier          → supplies                → Product/Part
Dealer            → performs                → Service Job (which installs the Part on the Machine)
```

---

## How the relationships feed each Parts Intelligence view

| View | Question it answers | Chain of relationships used |
|---|---|---|
| **Part matching** | "Which part do I need?" | Part → category, attributes → fits Machine |
| **Impact** | "What stops if this part is unavailable?" | Part → BOM → Assembly → Machine (+ open Sales Orders) |
| **Compliance** | "Which rules must this part meet, and where are the gaps?" | Part → Assembly → Machine → Compliance requirements, compared with the Part's own certifications |
| **Supplier Risk** | "How exposed are we?" | Part → Supplier (share, sole or dual source) → all parts of that Supplier |
| **Mitigation** | "What do we do about it?" | Part → Alternative Parts → their Supplier, Compliance and fit on the same Machines → ranked options |
| **Dealer / order questions** | "Where is my order? Who is my nearest dealer?" | Customer → Sales Order → Shipment → Dealer · Customer location → nearest Dealer |
