/**
 * Fixed header. Lives entirely in the DOM, never in the video.
 *
 * The brand mark, and the places the header can take you that scrolling
 * cannot. The story itself is navigated by scrolling, so a section menu here
 * would only duplicate the scrollbar with a second, competing way through
 * the same timeline — but the two applications are not on that timeline at
 * all, and no amount of scrolling reaches them.
 */
export function HeroNavigation({ onSeek, onOpenGround, onOpenOrdering }) {
  return (
    <header className="header">
      <a
        className="header__brand"
        href="#top"
        onClick={(event) => {
          event.preventDefault()
          onSeek(0)
        }}
      >
        <span className="header__brand-main">HITACHI</span>
        <span className="header__brand-sub">AFTER-SALES</span>
      </a>

      <nav className="header__nav" aria-label="Sections">
        <a
          className="header__link"
          href="#/the-ground"
          onClick={(event) => {
            event.preventDefault()
            onOpenGround()
          }}
        >
          The Ground
        </a>
        <a
          className="header__link"
          href="#/parts-ordering"
          onClick={(event) => {
            event.preventDefault()
            onOpenOrdering()
          }}
        >
          Parts Ordering
        </a>
      </nav>
    </header>
  )
}
