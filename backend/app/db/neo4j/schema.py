"""
backend/app/db/neo4j/schema.py

Applies Neo4j constraints and indexes at application startup.

Node labels and their constraints:
  FulfilmentRequest     — unique id
  FulfilmentOption      — unique id
  InventoryCache        — unique id
  InventoryLedger       — unique id  (composite key: partNumber:sourceId)
  Allocation            — unique id
  AuditRecord           — unique id
  IdempotencyRecord     — unique idempotencyKey + endpoint (composite)
  PartsInquiry          — unique id
  Customer              — unique email
"""

from __future__ import annotations

from typing import List

from app.logging_config.logger import logger

# Each entry is a Cypher statement that is idempotent (CREATE CONSTRAINT IF NOT EXISTS).
SCHEMA_STATEMENTS: List[str] = [
    # ---- FulfilmentRequest ------------------------------------------------
    """
    CREATE CONSTRAINT FulfilmentRequest_id IF NOT EXISTS
    FOR (n:FulfilmentRequest)
    REQUIRE n.id IS UNIQUE
    """,
    # ---- FulfilmentOption -------------------------------------------------
    """
    CREATE CONSTRAINT FulfilmentOption_id IF NOT EXISTS
    FOR (n:FulfilmentOption)
    REQUIRE n.id IS UNIQUE
    """,
    # ---- InventoryCache ---------------------------------------------------
    """
    CREATE CONSTRAINT InventoryCache_id IF NOT EXISTS
    FOR (n:InventoryCache)
    REQUIRE n.id IS UNIQUE
    """,
    # ---- InventoryLedger --------------------------------------------------
    """
    CREATE CONSTRAINT InventoryLedger_id IF NOT EXISTS
    FOR (n:InventoryLedger)
    REQUIRE n.id IS UNIQUE
    """,
    # ---- Allocation -------------------------------------------------------
    """
    CREATE CONSTRAINT Allocation_id IF NOT EXISTS
    FOR (n:Allocation)
    REQUIRE n.id IS UNIQUE
    """,
    # ---- Order (Phase 6) ---------------------------------------------------
    """
    CREATE CONSTRAINT Order_id IF NOT EXISTS
    FOR (n:Order)
    REQUIRE n.id IS UNIQUE
    """,
    # ---- AuditRecord ------------------------------------------------------
    """
    CREATE CONSTRAINT AuditRecord_id IF NOT EXISTS
    FOR (n:AuditRecord)
    REQUIRE n.id IS UNIQUE
    """,
    # ---- IdempotencyRecord ------------------------------------------------
    """
    CREATE CONSTRAINT IdempotencyRecord_key IF NOT EXISTS
    FOR (n:IdempotencyRecord)
    REQUIRE (n.idempotencyKey, n.endpoint) IS NODE KEY
    """,
    # ---- PartsInquiry -----------------------------------------------------
    """
    CREATE CONSTRAINT PartsInquiry_id IF NOT EXISTS
    FOR (n:PartsInquiry)
    REQUIRE n.id IS UNIQUE
    """,
    # ---- Customer ---------------------------------------------------------
    """
    CREATE CONSTRAINT Customer_email IF NOT EXISTS
    FOR (n:Customer)
    REQUIRE n.email IS UNIQUE
    """,

    # ---- Indexes (for query performance) ----------------------------------
    """
    CREATE INDEX FulfilmentRequest_status IF NOT EXISTS
    FOR (n:FulfilmentRequest)
    ON (n.status)
    """,
    """
    CREATE INDEX FulfilmentRequest_customerId IF NOT EXISTS
    FOR (n:FulfilmentRequest)
    ON (n.customerId)
    """,
    """
    CREATE INDEX FulfilmentOption_requestId IF NOT EXISTS
    FOR (n:FulfilmentOption)
    ON (n.fulfilmentRequestId)
    """,
    """
    CREATE INDEX InventoryCache_partNumber IF NOT EXISTS
    FOR (n:InventoryCache)
    ON (n.partNumber)
    """,
    """
    CREATE INDEX AuditRecord_entityId IF NOT EXISTS
    FOR (n:AuditRecord)
    ON (n.entityType, n.entityId)
    """,
    """
    CREATE INDEX Order_fulfilmentRequestId IF NOT EXISTS
    FOR (n:Order)
    ON (n.fulfilmentRequestId)
    """,

    # ---- Parts Intelligence: lexical full-text search over existing Part
    # nodes (no new Part model — same canonical Part identity used by the
    # rest of the Parts Store). Confirmed supported: Neo4j Kernel 5.27
    # Enterprise (AuraDB).
    """
    CREATE FULLTEXT INDEX part_fulltext_search IF NOT EXISTS
    FOR (p:Part)
    ON EACH [p.part_name, p.description, p.part_category, p.part_subcategory, p.part_number]
    """,

    # ---- Parts Intelligence: vector index foundation for semantic search.
    # Created defensively (skipped non-fatally by apply_schema if the Neo4j
    # edition/version in a given environment does not support it). No
    # embeddings are written to Part nodes yet — no EmbeddingProvider is
    # configured in this environment (see app/modules/intelligence/
    # providers.py). This index is dimensioned for a common embedding size
    # (1536) as a placeholder; update `vector.dimensions` to match whatever
    # real embedding model is wired in later.
    """
    CREATE VECTOR INDEX part_embedding_index IF NOT EXISTS
    FOR (p:Part) ON (p.embedding)
    OPTIONS {indexConfig: {
        `vector.dimensions`: 1536,
        `vector.similarity_function`: 'cosine'
    }}
    """,

    # ---- Operational/commercial context layer (HCME Europe KPI foundation)
    # See docs/research/HCME_EUROPE_OPERATIONAL_DATA_AND_KPI_FOUNDATION.md.
    # Depot is REAL (one verified node: Oosterhout). Supplier, CatalogEntry,
    # InventorySnapshot, Shipment, CustomsContext are SYNTHETIC-only labels
    # (every node written under them carries synthetic=true,
    # data_source='SYNTHETIC_DEMO' — enforced by
    # docs/data/neo4j/scripts/seed_operational_demo_data.py, never by this
    # schema file). Deliberately new/separate from Phase 6's real
    # InventoryCache/InventoryLedger labels so demo data can never be read
    # by the real availability/inventory code paths as if it were live.
    """
    CREATE CONSTRAINT Depot_id IF NOT EXISTS
    FOR (n:Depot)
    REQUIRE n.depot_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT Supplier_id IF NOT EXISTS
    FOR (n:Supplier)
    REQUIRE n.supplier_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT CatalogEntry_id IF NOT EXISTS
    FOR (n:CatalogEntry)
    REQUIRE n.catalog_entry_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT InventorySnapshot_id IF NOT EXISTS
    FOR (n:InventorySnapshot)
    REQUIRE n.snapshot_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT Shipment_id IF NOT EXISTS
    FOR (n:Shipment)
    REQUIRE n.shipment_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT CustomsContext_id IF NOT EXISTS
    FOR (n:CustomsContext)
    REQUIRE n.customs_context_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT DealerBranch_dealer_id IF NOT EXISTS
    FOR (n:DealerBranch)
    REQUIRE n.dealer_id IS UNIQUE
    """,
    # ---- ServiceJob (Phase 8) ---------------------------------------------
    """
    CREATE CONSTRAINT ServiceJob_id IF NOT EXISTS
    FOR (n:ServiceJob)
    REQUIRE n.service_job_id IS UNIQUE
    """,
    # ---- ServiceEvent (Phase 8) -------------------------------------------
    """
    CREATE CONSTRAINT ServiceEvent_id IF NOT EXISTS
    FOR (n:ServiceEvent)
    REQUIRE n.id IS UNIQUE
    """,
    # ---- ComplianceRequirement (Phase 7) ----------------------------------
    """
    CREATE CONSTRAINT ComplianceRequirement_id IF NOT EXISTS
    FOR (n:ComplianceRequirement)
    REQUIRE n.compliance_id IS UNIQUE
    """,
    # ---- ServiceJob Indexes -----------------------------------------------
    """
    CREATE INDEX ServiceJob_orderId IF NOT EXISTS
    FOR (n:ServiceJob)
    ON (n.order_id)
    """,
    """
    CREATE INDEX ServiceJob_dealerId IF NOT EXISTS
    FOR (n:ServiceJob)
    ON (n.dealer_id)
    """,
    """
    CREATE INDEX ServiceJob_status IF NOT EXISTS
    FOR (n:ServiceJob)
    ON (n.status)
    """,
]


def apply_schema(session) -> None:
    """
    Apply all constraints and indexes.  Safe to call on every startup
    because every statement uses IF NOT EXISTS.
    """
    logger.info("Applying Neo4j schema constraints and indexes …")
    for stmt in SCHEMA_STATEMENTS:
        cypher = stmt.strip()
        try:
            session.run(cypher).consume()
        except Exception as e:
            # Log but do not crash — some AuraDB tiers restrict certain
            # constraint syntax; the application can still operate.
            logger.warning(f"Schema statement skipped (non-fatal): {e}\n  Cypher: {cypher[:80]}")
    logger.info("Neo4j schema initialisation complete.")
