import { useCallback, useEffect, useState } from 'react'

import { Hero } from './sections/Hero/Hero'
import { AfterSalesEcosystem } from './sections/AfterSalesEcosystem/AfterSalesEcosystem'
import { PartsShowcase } from './sections/PartsShowcase/PartsShowcase'
import { ServiceExperience } from './sections/ServiceExperience/ServiceExperience'
import { UptimeClose } from './sections/UptimeClose/UptimeClose'
import { TheGround } from './ground/components/TheGround'
import { PartsOrdering } from './ordering/components/PartsOrdering'

const GROUND = '#/the-ground'
const ORDERING = '#/parts-ordering'

/**
 * Routing, such as it is.
 *
 * The project has no router and needs two routes, so this is the whole of
 * it: a hash the header sets and the page reads. A real router would be four
 * dependencies and a build change to serve three views, one of which is the
 * scrolling home page.
 *
 * The hash is the source of truth rather than component state, so the back
 * button works and the URL can be shared or reloaded.
 */
export default function App() {
  const [route, setRoute] = useState(() => window.location.hash)

  useEffect(() => {
    const onHash = () => setRoute(window.location.hash)
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  const openGround = useCallback(() => {
    window.location.hash = GROUND
    window.scrollTo(0, 0)
  }, [])

  const openOrdering = useCallback(() => {
    window.location.hash = ORDERING
    window.scrollTo(0, 0)
  }, [])

  const goHome = useCallback(() => {
    // Clearing rather than setting '#' keeps a bare '#' out of the URL.
    window.history.pushState('', '', window.location.pathname + window.location.search)
    setRoute('')
    window.scrollTo(0, 0)
  }, [])

  if (route === GROUND) return <TheGround onHome={goHome} onOpenOrdering={openOrdering} />

  if (route === ORDERING)
    return <PartsOrdering onHome={goHome} onOpenGround={openGround} />

  return (
    <>
      <Hero onOpenGround={openGround} onOpenOrdering={openOrdering} />

      {/* The landing point for "Explore Parts & Services" — it keeps the
          #after-sales anchor the Hero scrolls to. */}
      <AfterSalesEcosystem />

      <PartsShowcase />

      <ServiceExperience />

      <UptimeClose />
    </>
  )
}
