import type { MouseEvent } from 'react'
import './PartsStore.css'

import { SiteHeader } from '../../components/SiteHeader/SiteHeader'
import PartsIntelligencePanel from './PartsIntelligence'

/** sessionStorage key used to hand the chosen part number to the Parts Store
 *  screen — the one canonical Part selection path, same as a catalogue pick.
 *  See PartsStore.tsx's mount effect, which reads and clears this key. */
export const INTEL_HANDOFF_KEY = 'hcme-intel-selected-part'

/**
 * Parts Intelligence — its own screen, reached from the header nav or the
 * Parts Store's "Try Parts Intelligence" entry point. It is still the same
 * Parts Store application (frontend/, not a separate app) — this is a
 * second entry path into the one existing "Select Part" step, per the
 * two-entry-mode architecture (Normal Catalogue vs. Parts Intelligence)
 * that both converge on Select Part → Availability → Fulfilment → ... .
 */
export function PartsIntelligenceScreen({ onHome }: { onHome: () => void }) {
  const goToPartsStore = () => {
    window.location.hash = '#/parts-store'
    window.scrollTo(0, 0)
  }

  return (
    <main className="ps pi-screen" id="parts-intelligence">
      <SiteHeader
        position="sticky"
        current="parts-intelligence"
        onBrandClick={(event: MouseEvent<HTMLAnchorElement>) => {
          event.preventDefault()
          onHome()
        }}
      />

      <PartsIntelligencePanel
        onSelectPartNumber={(partNumber) => {
          // Hand off to the SAME Select Part step the normal catalogue uses,
          // then leave this screen — Parts Store's own mount effect resolves
          // the part number via findCatalogueMatchId, exactly as if it had
          // been picked from a product card.
          try {
            sessionStorage.setItem(INTEL_HANDOFF_KEY, partNumber)
          } catch {
            // sessionStorage unavailable (e.g. private mode) — fall back to
            // a plain navigation; Parts Store's search box still works.
          }
          goToPartsStore()
        }}
      />
    </main>
  )
}
