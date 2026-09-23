# Security Architecture

## 1. Authentication

**Mechanism: TO-BE.** Phase 1 confirms only that the existing Dealer Portal 2.0 requires a login (Phase 1 `HCME_CONFIRMED_VS_UNKNOWN.md`) — no specific identity provider, protocol, or credential model is confirmed for this platform.

- A candidate for HCME/dealer-staff identity is an enterprise SSO provider such as **Microsoft Entra ID** — named here explicitly as a **TO-BE candidate**, not a decision, because no Phase 1/HCME source confirms it is the required or available option.
- Customer authentication may reasonably differ from dealer/HCME staff authentication (a separate, possibly simpler identity model) — also TO-BE.
- Until a provider is chosen, the architecture requires only that every request carry a verifiable identity token, validated by the Authentication/Authorization module (`BACKEND_ARCHITECTURE.md`) at the API boundary, before any business module executes.

## 2. Authorization

- Enforced centrally, once, at the API layer (middleware in front of every `/api/v1/...` handler) — not re-implemented per module (`BACKEND_ARCHITECTURE.md` §2).
- Role/type model (minimum, derivable from Phase 1 `ACTORS_AND_RESPONSIBILITIES.md`): Customer, Dealer (Branch staff), Technician, HCME staff. Each endpoint in `API_ARCHITECTURE.md` states which of these may call it.

## 3. Dealer/customer access separation

- A Dealer Branch identity may act on Fulfilment Requests/Orders/Shipments/Service Jobs associated with its own branch/territory only — never another branch's data, and never another dealer's data.
- A Customer identity may act on and view only their own Fulfilment Requests/Orders.
- HCME staff have broader read access for support/audit purposes, but write access is still scoped per action (e.g., HCME staff cannot silently complete a Service Job on a dealer's behalf without an explicit, audited override path — not designed in this phase unless a business need is confirmed).

## 4. Backend-only secrets (principle 7)

- No credential, API key, or connection string for PostgreSQL, Neo4j, or any Integration Adapter is ever present in frontend code, a browser-visible response, or client-side storage. This is already the pattern in the existing codebase (`frontend/api/_lib/neo4j.js` reads credentials from server-side environment variables only) and this architecture extends the same rule to every new integration.
- All external-system credentials live in the Integrations module's configuration, loaded from environment variables (`ENVIRONMENT_CONFIGURATION.md`), never hardcoded.

## 5. HTTPS

All traffic — frontend↔backend and backend↔any external provider — is HTTPS-only. No plaintext HTTP path exists in any environment above local development (and even locally, credentials are never real production values — see `ENVIRONMENT_CONFIGURATION.md`).

## 6. Input validation

Every API endpoint validates its input at the boundary (`API_ARCHITECTURE.md` "Validation" row per endpoint) before any business logic runs — malformed input never reaches a domain module, let alone an external adapter call.

## 7. API authorization

Every endpoint requires a valid identity (§1) and passes an authorization check (§2, §3) before executing; there is no unauthenticated endpoint in `API_ARCHITECTURE.md`.

## 8. Rate limiting

Applied at the API boundary, per identity, to protect both the platform and any downstream external provider from excessive call volume — particularly important for Allocation (`ALLOCATION_ARCHITECTURE.md`), where a misbehaving client retrying rapidly should not be able to create load-based race conditions beyond what the locking design already tolerates. Exact limits are a Phase 3 tuning decision, not fixed here.

## 9. Audit logging

See `AUDIT_ARCHITECTURE.md` — every important business action is logged with actor, action, timestamp, and correlation ID; this is a security control as much as a business one (supports incident investigation).

## 10. Sensitive data handling

- Customer/dealer personal and contact data is stored only in PostgreSQL (not duplicated into Neo4j, per principle 11 and `NEO4J_ARCHITECTURE.md` §3).
- No sensitive data is logged in plaintext in application logs (`OBSERVABILITY_ARCHITECTURE.md`) — logs reference entity IDs, not personal data payloads.
- Data residency/privacy constraints specific to European customer/dealer data are an open question (Phase 1 `HCME_BUSINESS_QUESTIONS.md` Q27) — not resolved here.

## 11. Database credentials

PostgreSQL and Neo4j credentials are environment-specific (`ENVIRONMENT_CONFIGURATION.md`), rotated per HCME's eventual operational policy (TO-BE), and scoped to least privilege (§12) — e.g., the platform's database role has no more permission than the specific tables/operations each module needs.

## 12. External API credentials

Every Integration Adapter's credentials (once a real provider is confirmed — see `INTEGRATION_ARCHITECTURE.md`) are environment-specific and held only in backend configuration, never shared across environments, never in source control.

## 13. Webhook authentication

Any inbound webhook (e.g., a future `TrackingProvider` push — `SHIPMENT_ARCHITECTURE.md` §2) is authenticated by the sending provider's own signature/secret scheme; an unauthenticated or invalid-signature webhook call is rejected and logged, never processed as if trusted.

## 14. Least privilege

Applied consistently: each backend module's database access is scoped to only the tables it owns (`BACKEND_ARCHITECTURE.md` §1 "owns"/"must NOT own"); each Integration Adapter's external credential is scoped to only the operations that specific integration needs (e.g., a `TrackingProvider` credential need not have booking/write access if the provider distinguishes the two).
