# ADR-009 — Authentication Approach

## Context

Phase 1 confirms only that the existing Dealer Portal 2.0 requires a login — no identity provider, protocol, or credential model is confirmed for HCME generally or for this platform specifically (`HCME_CONFIRMED_VS_UNKNOWN.md`). The brief explicitly says not to select a specific enterprise identity provider unless Phase 1/HCME information supports it, while allowing a candidate to be named as TO-BE.

## Decision

**No authentication provider is selected in Phase 2.** The architecture fixes only the enforcement shape: every API request carries a validated identity token, checked once at the API boundary (`SECURITY_ARCHITECTURE.md` §1–2, `BACKEND_ARCHITECTURE.md`'s Authentication/Authorization module), before any business logic runs, with a role model of Customer / Dealer Branch staff / Technician / HCME staff. **Microsoft Entra ID is named as one TO-BE candidate** for dealer/HCME-staff identity (a plausible enterprise-SSO fit given HCME's likely existing Microsoft-centric IT environment), explicitly not a decision.

## Reason

- No confirmed source justifies committing to a specific provider — doing so would be inventing an HCME system/decision the research does not support (principle 13/14).
- Fixing the *enforcement shape* now (identity required, checked centrally, role-based authorization) lets every other architecture document (`API_ARCHITECTURE.md`'s per-endpoint authorization rows, `SECURITY_ARCHITECTURE.md`) be written concretely without waiting on the provider decision, since the shape does not change based on which provider is eventually chosen.

## Alternatives considered

| Alternative | Why not chosen |
|---|---|
| Select Microsoft Entra ID now, since it's a common enterprise choice | Rejected as a firm decision — "common" is not "confirmed for HCME"; the brief is explicit that this needs Phase 1/HCME support, which does not exist yet. Retained only as a named candidate. |
| Build a fully custom authentication system (username/password, own token issuance) | Not ruled out, but not chosen either — no evidence favours a custom build over an enterprise SSO integration once one is confirmed; deciding this now would be premature and outside this phase's evidence. |
| Leave authorization enforcement undesigned until a provider is chosen | Rejected — the role/enforcement *shape* does not depend on the provider, and every other document needs it to reference concretely; only the provider itself is deferred. |

## Consequences

- Every endpoint in `API_ARCHITECTURE.md` states its required role(s), independent of the eventual provider.
- Phase 3 (or an earlier dedicated decision point) must resolve this before real dealer/customer accounts can authenticate — it is the most consequential open item blocking real end-to-end testing beyond mocked identities.

## Status

Proposed (provider selection open; enforcement shape accepted).
