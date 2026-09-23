import type { MouseEvent } from 'react'
import './SiteHeader.css'

/**
 * The one header the whole site shares — the scrolling home page and the
 * Parts Store used to each carry their own copy, styled slightly
 * differently and drifting further apart every time one was edited and the
 * other wasn't. Now there is exactly one implementation.
 *
 * `position` is the one thing that legitimately differs by where the header
 * sits: fixed over the Hero's full-bleed scroll-video story so it never
 * pushes that section's frame math around, sticky in the Parts Store's
 * ordinary document flow. Everything else — markup, copy, colour, the nav
 * and cart — is identical.
 */
interface SiteHeaderProps {
  position?: 'fixed' | 'sticky'
  current?: string
  cartCount?: number
  onBrandClick?: (event: MouseEvent<HTMLAnchorElement>) => void
  onCartClick?: () => void
}

export function SiteHeader({
  position = 'fixed',
  current,
  cartCount = undefined,
  onBrandClick,
  onCartClick = undefined,
}: SiteHeaderProps) {
  const go = (event: MouseEvent<HTMLAnchorElement>, hash: string) => {
    event.preventDefault()
    window.location.hash = hash
    window.scrollTo(0, 0)
  }

  return (
    <header className={`site-header site-header--${position}`}>
      <a className="site-header__brand" href="#top" onClick={onBrandClick}>
        <span className="site-header__brand-main">HITACHI</span>
        <span className="site-header__brand-sub">AFTER-SALES</span>
      </a>

      <nav className="site-header__nav" aria-label="Primary">
        <a
          className={current === 'parts-store' ? 'site-header__link is-current' : 'site-header__link'}
          href="#/parts-store"
          onClick={(event) => go(event, '#/parts-store')}
        >
          Parts Store
        </a>
        <a
          className={current === 'parts-intelligence' ? 'site-header__link is-current' : 'site-header__link'}
          href="#/parts-intelligence"
          onClick={(event) => go(event, '#/parts-intelligence')}
        >
          Parts Intelligence
        </a>
        <a
          className={current === 'ground' ? 'site-header__link is-current' : 'site-header__link'}
          href="#/the-ground"
          onClick={(event) => go(event, '#/the-ground')}
        >
          The Ground
        </a>
      </nav>

      {typeof cartCount === 'number' && (
        onCartClick ? (
          <button type="button" className="site-header__cart" aria-label={`${cartCount} cart items — open cart`} onClick={onCartClick}>
            Cart <b>{cartCount}</b>
          </button>
        ) : (
          <div className="site-header__cart" aria-label={`${cartCount} cart items`}>
            Cart <b>{cartCount}</b>
          </div>
        )
      )}
    </header>
  )
}
