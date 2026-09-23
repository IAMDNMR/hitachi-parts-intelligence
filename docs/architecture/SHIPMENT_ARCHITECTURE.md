# Shipment Architecture

```
Order → Shipment → Carrier → Tracking → Delivery
```

Implements Phase 1 `SHIPMENT_PROCESS.md`.

## 1. Provider abstractions

| Interface | Responsibility |
|---|---|
| `ShipmentProvider` | Create a shipment with a carrier (or internal transfer mechanism) given an Order and its selected Fulfilment Option; returns a tracking reference. |
| `TrackingProvider` | Supply shipment events (dispatch, transit, delivery, exceptions) for a given tracking reference. |

Neither interface has a confirmed real implementation (`DATA_OWNERSHIP.md`, `HCME_CONFIRMED_VS_UNKNOWN.md`) — both exist so a future approved carrier can be integrated as an adapter without changing the Shipments module's own logic or the Order↔Shipment contract.

## 2. Event-driven vs. polling

Per the Phase 2 brief: **event/webhook-driven updates are preferred where a provider supports them; polling is a fallback only.** Architecturally:

- `TrackingProvider` implementations may push events (a webhook endpoint the platform exposes, authenticated per `SECURITY_ARCHITECTURE.md` §Webhook authentication) or be polled on an interval — the Shipments module's internal event-append logic (`STATE_TRANSITION_ARCHITECTURE.md` §C) is identical either way, since both paths converge on the same "append a Shipment Event, update status" operation.
- A shipment with no provider capable of either push or poll simply does not receive automated updates; its status can still be advanced by manual entry (e.g., a dealer confirming receipt) — the architecture does not require an automated tracking feed to exist for the process to function, consistent with "the process is designed so different approved logistics providers can eventually be integrated," not so that one is required today.

## 3. Failure handling

| Case | Handling |
|---|---|
| Shipment creation fails (`ShipmentProvider` error) | Order remains `ACCEPTED`; retried per `RESILIENCE_ARCHITECTURE.md` policy; no Shipment row is left in an ambiguous state. |
| Tracking event delivery fails/is delayed | Shipment status reflects the last known state; no assumption is made about what happened in the gap. |
| Webhook delivery fails (provider → platform) | If the provider supports polling as a fallback, the platform polls; if not, the shipment's status is only as fresh as the last successful event — this is a known, accepted limitation given no carrier integration is confirmed today, not a defect to solve speculatively. |

## 4. Carrier independence

No carrier is coupled into the Order or Fulfilment Option data model beyond a generic "provider" reference (`POSTGRESQL_DATA_ARCHITECTURE.md`). Swapping or adding a carrier is an `INTEGRATION_ARCHITECTURE.md`-level change (a new adapter registration), never a change to the Order, Shipment, or API contract shapes.

## 5. Delivery confirmation

Delivery is confirmed by whichever of these occurs first, both equally valid:

- A `TrackingProvider` event explicitly marking delivery.
- Manual confirmation by the receiving Dealer Branch (`DEALER_ARCHITECTURE.md`), for cases where no automated tracking exists.

Both paths converge on the same `Shipment → DELIVERED` transition (`STATE_TRANSITION_ARCHITECTURE.md` §C), and both are audited with their source clearly distinguished (carrier vs. manual).
