// =============================================================================
// Neo4j constraints — HCME After-Sales graph
// NOT EXECUTED. Design artifact only, for review before any Aura connection.
// Syntax: Neo4j 5.x / Aura-compatible (CREATE CONSTRAINT ... IF NOT EXISTS ... REQUIRE ... IS UNIQUE)
// =============================================================================

// One constraint per node label that is actually imported in this phase.
// No constraint is created for a label with zero current rows.

CREATE CONSTRAINT category_id_unique IF NOT EXISTS
FOR (n:Category) REQUIRE n.category_id IS UNIQUE;

CREATE CONSTRAINT machine_id_unique IF NOT EXISTS
FOR (n:Machine) REQUIRE n.machine_id IS UNIQUE;

CREATE CONSTRAINT spec_id_unique IF NOT EXISTS
FOR (n:Specification) REQUIRE n.spec_id IS UNIQUE;

CREATE CONSTRAINT application_name_unique IF NOT EXISTS
FOR (n:Application) REQUIRE n.name IS UNIQUE;

CREATE CONSTRAINT part_id_unique IF NOT EXISTS
FOR (n:Part) REQUIRE n.part_id IS UNIQUE;

CREATE CONSTRAINT attachment_id_unique IF NOT EXISTS
FOR (n:Attachment) REQUIRE n.attachment_id IS UNIQUE;

CREATE CONSTRAINT service_id_unique IF NOT EXISTS
FOR (n:Service) REQUIRE n.service_id IS UNIQUE;

CREATE CONSTRAINT digital_service_id_unique IF NOT EXISTS
FOR (n:DigitalService) REQUIRE n.digital_service_id IS UNIQUE;

CREATE CONSTRAINT channel_id_unique IF NOT EXISTS
FOR (n:Channel) REQUIRE n.channel_id IS UNIQUE;

// Added for the HCME Europe dealer-network import (see
// docs/research/HCME_EUROPE_PARTS_AND_DEALER_DATA_RESEARCH.md). DealerBranch
// was previously documented as TO-BE in DATA_OWNERSHIP.md / DEALER_ARCHITECTURE.md
// with no source data; this constraint backs the now-populated label.
CREATE CONSTRAINT dealer_branch_id_unique IF NOT EXISTS
FOR (n:DealerBranch) REQUIRE n.dealer_id IS UNIQUE;

// Existence constraints on the property that carries the evidence classification,
// so a HAS_PART_FITMENT / HAS_SERVICE edge can never be created without it —
// this is the single most important guardrail against evidence being silently lost.
CREATE CONSTRAINT part_record_class_exists IF NOT EXISTS
FOR (n:Part) REQUIRE n.record_class IS NOT NULL;
