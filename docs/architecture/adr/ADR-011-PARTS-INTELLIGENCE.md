# ADR-011 — Parts Intelligence as an entry path into the existing Parts Store

> **UPDATE (2026-09-22):** the Parts Store's own Node/Vercel-style API layer
> (`frontend/api/part-enrichment.js`, `frontend/api/quote-request.js`) has
> been consolidated into FastAPI (`backend/app/api/v1/part_enrichment.py`,
> `backend/app/api/v1/quote_request.py`). Parts Intelligence's own routes
> (`backend/app/api/v1/intelligence.py`) were already on FastAPI and are
> unaffected. The platform now has exactly one backend surface — `/api/v1/*`
> on FastAPI — for both the normal Parts Store and Parts Intelligence.

## Context

The platform has two application roots (`frontend/`, React+TS+Vite; `backend/`,
Python+FastAPI) and one runtime database (Neo4j, AuraDB Enterprise 5.27),
holding the canonical `(:Part)`/`(:Machine)`/`(:Category)`/`(:Service)`
graph (`docs/data/neo4j/import/` — the historical load scripts; the data is
already live in AuraDB: 60 `Part` nodes, 77 `Machine` nodes, confirmed
`HAS_PART_FITMENT` / `BELONGS_TO` / `HAS_SERVICE` / `HAS_SPECIFICATION`
relationships).

The Phase 1–5 Parts Store / Availability / Fulfilment / Allocation journey
(Select Part → Availability → Fulfilment Options → Allocate → Order →
Shipment → Dealer → Service → Close) is complete, tested, and frozen. The
requirement is to add a natural-language / semantic "Parts Intelligence"
entry point into the *same* Select Part step — not a separate AI
application, database, or vector store.

## Decision

1. **No new Part model.** Parts Intelligence reads the same `(:Part)` nodes
   the rest of the platform uses, keyed by the same `part_id`/`part_number`.
2. **New backend module, same app:** `backend/app/modules/intelligence/`
   (schemas, providers, query_parser, search, fitment, alternatives,
   ranking, explanation, service), exposed via
   `backend/app/api/v1/intelligence.py` under the existing `/api/v1` prefix.
   It is read-only: it never calls into allocation/order/shipment mutation
   paths.
3. **Search is Neo4j-native, no second search database:**
   - Exact: `MATCH` on `part_id`/`part_number`.
   - Lexical: a native Neo4j **FULLTEXT** index, `part_fulltext_search`
     (created idempotently in `backend/app/db/neo4j/schema.py`), over
     `part_name`, `description`, `part_category`, `part_subcategory`,
     `part_number`.
   - Semantic: a native Neo4j **VECTOR** index, `part_embedding_index`
     (also created idempotently), confirmed supported on this AuraDB
     instance (Neo4j Kernel 5.27, edition `enterprise`). No embeddings are
     written yet — see "LLM/embedding status" below.
4. **LLM/EmbeddingProvider abstraction** (`providers.py`): not tied to one
   vendor. `EmbeddingProvider` still resolves to `NullEmbeddingProvider`
   (semantic search reports itself as unused rather than pretending to
   run) — no embedding provider is configured.

   `LLMProvider` now has a real implementation, `GeminiLLMProvider`,
   wired behind the same abstraction:
   - Configured via `GEMINI_API_KEY` (read through `app.config.settings`,
     the existing pydantic-settings/`.env` pattern used by every other
     backend setting; optional `GEMINI_MODEL`, default
     `gemini-2.5-flash-lite`). The user sets the real value in
     `backend/.env`; it is never hardcoded, logged, or returned in any API
     response.
   - `get_llm_provider()` returns `GeminiLLMProvider` when
     `GEMINI_API_KEY` is set, else `DeterministicLLMProvider` — same
     fallback behaviour as before Gemini was wired.
   - Calls Gemini's `generateContent` REST endpoint directly via `httpx`
     (already a dependency; no new package added) with an 8s timeout, so a
     hanging call cannot block a Parts Intelligence request indefinitely.
   - **Strictly two responsibilities, both non-authoritative:**
     (a) turning a free-text query into the same `ParsedIntent` shape the
     deterministic parser produces (`query_parser.py`), and
     (b) phrasing an already-graph-verified `Evidence` list into a
     user-friendly sentence (`providers.py::GeminiLLMProvider.explain`,
     invoked from `service.py::_to_candidate` after `build_evidence` has
     run against Neo4j). Gemini receives the evidence as input and is
     explicitly instructed not to invent facts beyond it — it never runs
     before graph validation, and its output never feeds back into
     fitment, availability, pricing, allocation, ordering, shipment, or
     approval logic (`fitment.py`, `search.py`'s exact/lexical paths,
     `alternatives.py`, and the allocation/order/fulfilment modules do not
     import `providers.py` at all).
   - **Failure isolation:** any Gemini failure (timeout, HTTP error, bad
     JSON) raises `GeminiProviderError` inside the provider only;
     `query_parser.parse_query` catches it and falls back to
     `DeterministicLLMProvider`, and `service.py::_explain` catches it and
     falls back to the deterministic `build_explanation_text`. Both paths
     set the response's existing `degraded`/`degraded_reason` fields
     rather than raising — the Parts Store catalogue/availability/
     fulfilment flows do not call into this module and are unaffected by
     any Gemini outage.
5. **Graph-aware validation is mandatory.** A semantic/lexical match is a
   *candidate*, never a fitment claim, until checked against
   `(:Machine)-[:HAS_PART_FITMENT]->(:Part)`.
6. **UI:** added to the existing Parts Store page
   (`frontend/pages/PartsStore/`), not a new app — `PartsIntelligence.tsx`
   (natural-language box + result cards) and `GraphInsights.tsx` (one
   reusable 4-tab panel: Impact / Fitment & Evidence / Source & Availability
   / Alternatives). Selecting a candidate resolves to the *same* catalogue
   product id used by the normal Select Part flow
   (`intelligenceMatch.ts::findCatalogueMatchId`), so Availability/
   Fulfilment downstream is identical regardless of entry path.
7. **Failure isolation:** `service.py::search` catches Neo4j/search errors
   and returns a `degraded` response with a human-readable reason; the
   normal catalogue search and Availability/Fulfilment do not depend on
   Parts Intelligence and keep working if it is unavailable.

## Reason

Reuses the existing canonical Part graph and existing FastAPI/Neo4j stack
instead of standing up a parallel AI/vector service, satisfying the
"one canonical Part, one Parts Store journey" constraint while giving a
real, evidence-backed natural-language entry point.

## Consequences

- `part_embedding_index` exists but is empty until a real embedding
  provider and a controlled embedding-generation job are added — documented
  as a blocker, not hidden. Gemini is not used for embeddings in this
  change; only `LLMProvider` (query understanding + explanation) is wired.
- `DeterministicLLMProvider` is a plain pattern matcher, not an LLM; its
  `ParsedIntent.source` is `"deterministic"` whenever `GEMINI_API_KEY` is
  unset, or whenever Gemini is configured but a call fails and the
  request degrades — `"llm"` only reflects a real, successful Gemini
  response, so the UI/API never implies a real model ran when one didn't.
- Availability shown from Intelligence is always `UNKNOWN`/contextual —
  the authoritative Availability check remains
  `backend/app/modules/availability/service.py`, untouched by this change.
