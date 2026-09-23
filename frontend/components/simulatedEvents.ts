/**
 * Data-truth wording for the fulfilment lifecycle demonstration.
 *
 * The lifecycle screens run on SYNTHETIC_DEMO data: inventory is simulated, the carrier/TMS, SAP ERP ordering and dealer
 * DMS/service systems are NOT_CONNECTED. The backend stores event descriptions written as if the events were real
 * (e.g. "physically installed", "Quality inspection passed", role CERTIFIED_SERVICE_TECHNICIAN); the UI must not repeat them.
 * These helpers replace them with explicit [SIMULATED] milestone labels. Display only - no API or state-machine change.
 */

const SERVICE_LABELS: Record<string, string> = {
  CREATED: '[SIMULATED] Service Job Created',
  PART_RECEIVED: '[SIMULATED] Part Receipt Recorded',
  IN_PROGRESS: '[SIMULATED] Service Work Started',
  PART_INSTALLED: '[SIMULATED] Installation Milestone Recorded',
  COMPLETED: '[SIMULATED] Service Completion Recorded',
  CANCELLED: '[SIMULATED] Service Job Cancelled',
}

const SHIPMENT_LABELS: Record<string, string> = {
  CREATED: '[SIMULATED] Demonstration shipment record created.',
  DISPATCHED: '[SIMULATED] Demonstration shipment marked as dispatched.',
  IN_TRANSIT: '[SIMULATED] Demonstration shipment marked as in transit.',
  EXCEPTION: '[SIMULATED] Demonstration shipment exception recorded.',
  DELIVERED: 'Demonstration shipment reached the simulated delivery milestone.',
  CANCELLED: '[SIMULATED] Demonstration shipment cancelled.',
}

export function simulatedServiceEvent(eventType: string): string {
  return SERVICE_LABELS[eventType] ?? `[SIMULATED] Service milestone recorded (${eventType})`
}

export function simulatedShipmentEvent(eventType: string): string {
  return SHIPMENT_LABELS[eventType] ?? `[SIMULATED] Demonstration shipment event (${eventType})`
}
