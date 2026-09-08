/** The after-sales route, from a problem in the field back to a working machine. */
export const journeySteps = [
  { id: 'issue', label: 'ISSUE' },
  { id: 'identify', label: 'IDENTIFY PART' },
  { id: 'availability', label: 'CHECK AVAILABILITY' },
  { id: 'order', label: 'ORDER' },
  { id: 'supply', label: 'SUPPLY' },
  { id: 'dealer', label: 'DEALER' },
  { id: 'technician', label: 'TECHNICIAN' },
  { id: 'repair', label: 'REPAIR' },
  { id: 'uptime', label: 'UPTIME', terminal: true },
]
