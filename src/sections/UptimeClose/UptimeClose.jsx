import { useCallback, useEffect, useRef, useState } from 'react'
import './UptimeClose.css'

import { uptimePillars, chapters, footerLinks } from '../../data/uptimeClose'
import { UptimeIcon } from './UptimeIcons'
import machineOnSite from '../../../assets/source/section-04/service-frames/frame-085.webp'

/**
 * Reveals the section's contents one element at a time, once it comes into
 * view. An IntersectionObserver rather than a scroll listener: the browser
 * does the work off the main thread, it fires once, and it costs nothing
 * while the reader is anywhere else on a 26-screen page.
 *
 * The stagger itself is CSS — each child carries its own `--i`, so the
 * order lives with the markup rather than in a timeline here.
 */
function useRevealOnce() {
  const ref = useRef(null)
  const [shown, setShown] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el || shown) return undefined

    // Anyone who asked for less motion gets the finished state immediately.
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setShown(true)
      return undefined
    }

    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setShown(true)
          io.disconnect()
        }
      },
      { threshold: 0.2 },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [shown])

  return [ref, shown]
}

/**
 * Section 05 — UPTIME, and the page's footer.
 *
 * The one section that does not scrub. Every section before it is a pinned
 * scroll narrative; this one is where the page stops moving and settles, so
 * it is an ordinary block of layout. Making it scrub too would have meant
 * the page never resolves.
 *
 * The machine is a still from the service footage — the outdoor frame where
 * the machine is back at work, which is exactly what this section says. It
 * is treated the way Section 04 treats the same material: graded warm and
 * feathered into the page on all four sides, so it never reads as a
 * photograph in a box.
 */
export function UptimeClose({ onOpenGround, onOpenOrdering }) {
  const [sectionRef, shown] = useRevealOnce()

  const explore = useCallback(() => {
    document.getElementById('after-sales')?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  const toTop = useCallback(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [])

  return (
    <>
      <section
        className={shown ? 'up is-shown' : 'up'}
        ref={sectionRef}
        id="uptime"
        aria-labelledby="up-title"
      >
        <ChapterRail />

        <div className="up__grid">
          <figure className="up__stage up__reveal" style={{ '--i': 0 }}>
            <Halo />
            <img
              className="up__machine"
              src={machineOnSite}
              alt="A Hitachi excavator back at work on site"
              decoding="async"
              loading="lazy"
            />
          </figure>

          <div className="up__copy">
            <p className="up__kicker up__reveal" style={{ '--i': 0 }}>
              <span className="up__kicker-rule" aria-hidden="true" />
              Uptime
            </p>

            <h2 className="up__title" id="up-title">
              <span className="up__reveal" style={{ '--i': 1 }}>
                The machine
              </span>
              <span className="up__title-accent up__reveal" style={{ '--i': 2 }}>
                works.
              </span>
            </h2>

            <p className="up__sub up__reveal" style={{ '--i': 3 }}>
              <span className="up__sub-rule" aria-hidden="true" />
              The journey continues.
            </p>

            <p className="up__body up__reveal" style={{ '--i': 4 }}>
              Your Hitachi machine is supported by expert care, genuine parts
              and intelligent insight — built for the long run.
            </p>

            <button
              type="button"
              className="up__cta up__reveal"
              style={{ '--i': 5 }}
              onClick={explore}
            >
              Explore the after-sales ecosystem
              <UptimeIcon name="arrow" size={18} />
            </button>
          </div>
        </div>

        <ul className="up__pillars">
          {uptimePillars.map((p, i) => (
            <li className="up__reveal" key={p.id} style={{ '--i': 6 + i }}>
              <span className="up__pillar-badge">
                <UptimeIcon name={p.icon} size={22} />
              </span>
              <span className="up__pillar-copy">
                <span className="up__pillar-title">{p.title}</span>
                {p.lines.map((line) => (
                  <span className="up__pillar-line" key={line}>
                    {line}
                  </span>
                ))}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <SiteFooter
        onToTop={toTop}
        onOpenGround={onOpenGround}
        onOpenOrdering={onOpenOrdering}
      />
    </>
  )
}

/** Where the reader is in the page. The last chapter, so the last mark is lit. */
function ChapterRail() {
  return (
    <div className="up__rail" aria-hidden="true">
      <ol>
        {chapters.map((name, i) => (
          <li key={name} className={i === chapters.length - 1 ? 'is-active' : undefined}>
            <span className="up__rail-dot" />
            {i === chapters.length - 1 && (
              <span className="up__rail-label">{name}</span>
            )}
          </li>
        ))}
      </ol>
    </div>
  )
}

/**
 * Concentric arcs behind the machine. Geometry rather than decoration: three
 * rings and nothing else, at an opacity that reads as light rather than as
 * a graphic.
 */
function Halo() {
  return (
    <svg className="up__halo" viewBox="0 0 600 600" fill="none" aria-hidden="true">
      <g stroke="rgba(214,138,58,0.32)" strokeWidth="1">
        <circle cx="300" cy="300" r="288" />
        <circle cx="300" cy="300" r="232" />
        <circle cx="300" cy="300" r="176" />
      </g>
    </svg>
  )
}

function SiteFooter({ onToTop, onOpenGround, onOpenOrdering }) {
  /* The three destinations named in data/uptimeClose.js. Kept here rather
     than in the data so the data stays declarative — it says where, this
     says how. */
  const go = {
    ground: () => onOpenGround(),
    ordering: () => onOpenOrdering(),
    top: onToTop,
  }

  return (
    <footer className="foot">
      <div className="foot__inner">
        <div className="foot__brand">
          <span className="foot__brand-main">Hitachi</span>
          <span className="foot__brand-sub">After-Sales</span>
        </div>

        <p className="foot__line">
          Built to perform. <span className="foot__line-accent">Supported to last.</span>
        </p>

        {/* Real destinations, not placeholders. This was four inert spans —
            Privacy Policy, Terms of Use, Cookies, Sitemap — for pages that do
            not exist. The header offers the two applications, and by the time
            anyone reaches this footer the header is five sections of scrolling
            away. */}
        <ul className="foot__links">
          {footerLinks.map((link) => (
            <li key={link.to}>
              <button type="button" className="foot__link" onClick={go[link.to]}>
                {link.label}
              </button>
            </li>
          ))}
        </ul>

        <p className="foot__legal">
          © Hitachi Construction Machinery. All rights reserved.
        </p>

        <button
          type="button"
          className="foot__top"
          onClick={onToTop}
          aria-label="Back to top"
        >
          <UptimeIcon name="arrowUp" size={18} />
        </button>
      </div>
    </footer>
  )
}
