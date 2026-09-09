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

  /* Optionally onto a specific node — the hero's domain panels open the map
     already standing on the thing the reader was reading about. Called with
     no argument (or with a click event, from the header links) it opens the
     map where it always did. */
  const openGround = useCallback((nodeId) => {
    window.location.hash = typeof nodeId === 'string' ? `${GROUND}/${nodeId}` : GROUND
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

  /* Matched by prefix, not by equality.
     The Ground writes the selected node into the hash — `#/the-ground/sys-d365`
     — so a node can be linked to and survives a reload. Compared with `===`
     that hash matches no route at all and the whole page silently fell
     through to the scrolling home page. Anything after the route name belongs
     to the route and is read by the view itself. */
  const on = (base) => route === base || route.startsWith(`${base}/`)

  if (on(GROUND)) return <TheGround onHome={goHome} onOpenOrdering={openOrdering} />

  if (on(ORDERING)) return <PartsOrdering onHome={goHome} onOpenGround={openGround} />

  return (
    <>
      <Hero onOpenGround={openGround} onOpenOrdering={openOrdering} />

      {/* The landing point for "Explore Parts & Services" — it keeps the
          #after-sales anchor the Hero scrolls to. */}
      <AfterSalesEcosystem />

      <PartsShowcase />

      <ServiceExperience />

      {/* The footer offers the two applications. By this point the header
          that also offers them is five sections of scrolling away. */}
      <UptimeClose onOpenGround={openGround} onOpenOrdering={openOrdering} />
    </>
  )
}
