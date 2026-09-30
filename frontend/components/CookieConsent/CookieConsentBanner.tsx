import { useEffect, useState } from 'react'
import { acceptCookies, declineCookies, getConsent, startAnalytics } from '../../lib/analytics'
import './CookieConsentBanner.css'

/**
 * Site-wide cookie banner. Shown once, before any tracking cookie is set — required because this site is
 * EU-only (GDPR/ePrivacy). Nothing in lib/analytics.ts runs until "Accept" is clicked.
 */
export function CookieConsentBanner() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const consent = getConsent()
    if (consent === 'accepted') {
      startAnalytics() // already agreed on an earlier visit
    } else if (consent === null) {
      setVisible(true)
    }
  }, [])

  if (!visible) return null

  return (
    <div className="cc-banner" role="dialog" aria-label="Cookie consent" aria-live="polite">
      <div className="cc-banner__body">
        <p>
          We use first-party cookies to understand how the site is used — pages viewed, time spent, your IP
          address, your approximate location worked out from it (via a lookup service, never a precise address),
          and your device/browser type. No data is sold or shared with advertisers, and nothing runs until you
          accept.
        </p>
      </div>
      <div className="cc-banner__actions">
        <button
          type="button"
          className="cc-banner__btn cc-banner__btn--ghost"
          onClick={() => {
            declineCookies()
            setVisible(false)
          }}
        >
          Decline
        </button>
        <button
          type="button"
          className="cc-banner__btn cc-banner__btn--primary"
          onClick={() => {
            acceptCookies()
            setVisible(false)
          }}
        >
          Accept
        </button>
      </div>
    </div>
  )
}
