import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import './machinery.css'

import {
  MACHINES,
  VISUAL_CATEGORIES,
  categoryById,
  machineById,
  type Category,
  type Machine,
} from '../../data/machineCatalogue'
import { LandcrosBand } from './LandcrosBand'
import { ModelShowcase } from './ModelShowcase'
import { MachineImage } from './MachineImage'

/**
 * SECTION — MACHINERY.
 *
 * The machine universe, as one section of the scrolling page rather than a page
 * of its own. Machinery -> Category -> Model -> Machine happens inside this
 * section: the three views replace each other in place and the page around them
 * — hero, ecosystem, parts, service — is never left.
 *
 * That is why there is no route here and no second router. Drilling in is state,
 * not navigation, so the reader keeps their place on the page and the browser's
 * back button still means "the previous page", which on a one-page site is what
 * it should mean.
 *
 * Nothing about the taxonomy lives in this file. The seven visual categories,
 * their machines, their names and their photographs all come from
 * data/machineCatalogue.ts, generated from the frozen workbook and the image
 * manifest. Adding a machine to the data adds it to the screen.
 *
 * The five excavator categories and the two top-level categories are drawn as
 * two groups because they ARE two things: Mini, Medium, Large, Wheeled and
 * Special Applications are subcategories of Excavators; Wheel Loaders and Rigid
 * Dump Trucks are not.
 */

const HASH = '#machinery'

/** `#machinery/large/MC-024` -> { categoryId: 'large', machineId: 'MC-024' } */
export function readMachineryHash(): { categoryId: string | null; machineId: string | null } {
  const h = typeof window === 'undefined' ? '' : window.location.hash
  if (!h.startsWith(HASH)) return { categoryId: null, machineId: null }
  const [categoryId, machineId] = h.slice(HASH.length).replace(/^\//, '').split('/')
  return { categoryId: categoryId || null, machineId: machineId || null }
}

/**
 * What a category is called in a heading.
 *
 * "Mini" needs its parent to make sense as a title — Mini what? — so the four
 * size categories read as "Mini Excavators". "Special Applications" is already a
 * complete name and would otherwise become "Special Applications Excavators",
 * which is not a thing. Wheel Loaders and Rigid Dump Trucks name themselves.
 */
function categoryTitle(category: Category | null): string {
  if (!category) return 'Machinery'
  if (category.parent !== 'Excavators' || category.id === 'special') return category.label
  return `${category.label} Excavators`
}

export function MachinerySection() {
  /* Where the reader is, kept in the URL rather than in component state.
     `#machinery` is the ring, `#machinery/large` a category, and
     `#machinery/large/MC-024` a machine.

     This is still one section of one page - the drill-down replaces the
     section's contents and never leaves the scrolling page - but putting it in
     the hash means the browser's own Back button walks back out of it, a
     category can be linked to, and a reload lands where you were. With it in
     useState, Back left the page entirely and the reader lost their place. */
  const [route, setRoute] = useState(readMachineryHash)

  useEffect(() => {
    const sync = () => setRoute(readMachineryHash())
    window.addEventListener('hashchange', sync)
    return () => window.removeEventListener('hashchange', sync)
  }, [])

  const { categoryId, machineId } = route
  const category = categoryId ? categoryById(categoryId) : null
  const machine = machineId ? machineById(machineId) : null

  const root = useRef<HTMLElement>(null)
  /* Skip the first run: the section must not pull the page to itself while the
     reader is still up in the hero. It only re-anchors once they have drilled in. */
  const touched = useRef(false)

  /* The machine the reader has just come back from, if any, so the showcase
     can put them on it again instead of starting the category over. */
  const lastMachine = useRef<string | null>(null)
  const resumeId = !machineId && categoryId ? lastMachine.current : null
  useEffect(() => {
    lastMachine.current = machineId
  }, [machineId])

  useEffect(() => {
    if (!touched.current) {
      touched.current = true
      return
    }
    // Returning to a category from one of its machines: the showcase scrolls
    // itself to that machine.
    if (resumeId) return
    const el = root.current
    if (!el) return
    // The showcase pins at the very top of the section; the other views keep a
    // little air above them.
    const offset = category && !machine ? 0 : 24
    const top = el.getBoundingClientRect().top + window.scrollY - offset
    window.scrollTo({ top, behavior: 'smooth' })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [categoryId, machineId])

  /* Assigning the hash rather than replacing it, so each step is a history
     entry and Back is the reverse of the click that got here. */
  const openCategory = useCallback((id: string) => {
    window.location.hash = `${HASH}/${id}`
  }, [])

  const openMachine = useCallback(
    (id: string) => {
      window.location.hash = `${HASH}/${categoryId}/${id}`
    },
    [categoryId],
  )

  const backToCategories = useCallback(() => {
    window.location.hash = HASH
  }, [])

  const backToCategory = useCallback(() => {
    window.location.hash = `${HASH}/${categoryId}`
  }, [categoryId])

  return (
    <section
      className={`mc${!category ? ' mc--entry' : machine ? '' : ' mc--show'}`}
      id="machinery"
      ref={root}
      aria-labelledby="mc-title"
    >
      <div className="mc__inner">
        {/* The breadcrumb belongs to a machine's own page. The showcase carries
            its category in its own type, and nothing sits above its pin. */}
        {machine && (
          <Trail
            category={category}
            machine={machine}
            onAll={backToCategories}
            onCategory={backToCategory}
          />
        )}

        {machine ? (
          <MachineDetail machine={machine} category={category} onBack={backToCategory} />
        ) : category ? (
          <ModelShowcase
            key={category.id}
            category={category}
            onOpenMachine={openMachine}
            onBack={backToCategories}
            resumeId={resumeId}
          />
        ) : (
          <Entry onOpen={openCategory} />
        )}
      </div>
    </section>
  )
}

interface TrailProps {
  category: Category | null
  machine: Machine | null
  onAll: () => void
  onCategory: () => void
}

/** Machinery / Large / ZX350LC-7 — and every step of it is the way back. */
function Trail({ category, machine, onAll, onCategory }: TrailProps) {
  if (!category) return null
  return (
    <nav className="mc__trail" aria-label="Machinery breadcrumb">
      <button className="mc__trail-item" type="button" onClick={onAll}>
        Machinery
      </button>
      <span className="mc__trail-sep" aria-hidden="true">
        /
      </span>
      {machine ? (
        <button className="mc__trail-item" type="button" onClick={onCategory}>
          {category.label}
        </button>
      ) : (
        <span className="mc__trail-item is-current" aria-current="true">
          {category.label}
        </span>
      )}
      {machine && (
        <>
          <span className="mc__trail-sep" aria-hidden="true">
            /
          </span>
          <span className="mc__trail-item is-current" aria-current="true">
            {machine.model}
          </span>
        </>
      )}
    </nav>
  )
}

/* ---------------------------------------------------------------- entry ---- */

/**
 * The collection.
 *
 * Seven categories set out like machines on a showroom floor: a back row of
 * four and a front row of three standing in the gaps between them. It replaced
 * a ring of seven around a titled hub, which read as a diagram, needed ~900px
 * of height, and put everything below Medium under the fold at 1440 x 900.
 *
 * The back row is the excavator size story left to right - Mini, Medium,
 * Large, then Wheeled - and the front row carries Special Applications and the
 * two machine families that are not excavators. The front row is drawn a
 * little larger than the back, which is the whole of the depth cue: no floor,
 * no perspective, no orbit.
 *
 * Placement is by slot, in CSS, not inline: the same seven buttons become a
 * swipeable row on a phone, and an inline grid position would survive into
 * that layout and break it.
 */
const COLLECTION = ['mini', 'medium', 'large', 'wheeled', 'special', 'wheel-loaders', 'dump-trucks']

/* Reliable, Productive, Sustainable are Hitachi's own three words for the range
   and appear on HCME's construction-machinery pages. The line under each is a
   plain restatement of that word, not a claim about a product. */
const VALUES: { label: string; line: string; icon: ReactNode }[] = [
  {
    label: 'Reliable',
    line: 'Performance you can count on.',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
        <path d="M12 2.8 4.5 5.6v5.6c0 4.6 3.1 8.4 7.5 10 4.4-1.6 7.5-5.4 7.5-10V5.6z" strokeLinejoin="round" />
        <path d="m8.6 12 2.4 2.4 4.4-4.6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    label: 'Productive',
    line: 'Solutions that keep you moving.',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
        <circle cx="12" cy="12" r="3" />
        <path
          d="M10.3 2.8h3.4l.5 2.5a7.2 7.2 0 0 1 1.9 1.1l2.4-.8 1.7 2.9-1.9 1.7a7.2 7.2 0 0 1 0 2.2l1.9 1.7-1.7 2.9-2.4-.8a7.2 7.2 0 0 1-1.9 1.1l-.5 2.5h-3.4l-.5-2.5a7.2 7.2 0 0 1-1.9-1.1l-2.4.8-1.7-2.9 1.9-1.7a7.2 7.2 0 0 1 0-2.2L3.8 8.5l1.7-2.9 2.4.8a7.2 7.2 0 0 1 1.9-1.1z"
          strokeLinejoin="round"
        />
      </svg>
    ),
  },
  {
    label: 'Sustainable',
    line: 'A stronger tomorrow.',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
        <path d="M19.5 4.5c0 8-4.6 12.3-10.4 12.3-2.2 0-4-.6-4-.6s-.3-6 3.6-9.2c3.4-2.8 10.8-2.5 10.8-2.5z" strokeLinejoin="round" />
        <path d="M4.5 19.5c1.6-4 4.6-7 8.4-9" strokeLinecap="round" />
      </svg>
    ),
  },
]

function Entry({ onOpen }: { onOpen: (id: string) => void }) {
  const pieces = useMemo(
    () => COLLECTION.map(categoryById).filter((c): c is Category => c !== null),
    [],
  )

  return (
    <>
      <div className="mc-stage">
        {/* The ground: a warm gradient with a fine grain, one long orange arc
            sweeping between the words and the machines, and faint rings at the
            right edge. All of it decoration. */}
        <div className="mc-stage__plate" aria-hidden="true" />
        <span className="mc-stage__arc" aria-hidden="true" />
        <span className="mc-stage__rings" aria-hidden="true" />

        <div className="mc-stage__inner">
          <div className="mc-stage__lede">
            <p className="mc__eyebrow">The machines</p>
            <h2 className="mc-stage__title" id="mc-title">
              Machinery
            </h2>
            <p className="mc-stage__strap">Built for every kind of work</p>
            <span className="mc-stage__rule" aria-hidden="true" />
            <p className="mc-stage__body">
              The Hitachi range for Europe, from one-tonne mini excavators to 800-tonne mining machines.
              Everything after-sales hangs off one of these.
            </p>

            <ul className="mc-stage__values">
              {VALUES.map((v) => (
                <li className="mc-value" key={v.label}>
                  <span className="mc-value__icon" aria-hidden="true">
                    {v.icon}
                  </span>
                  <span className="mc-value__text">
                    <span className="mc-value__label">{v.label}</span>
                    <span className="mc-value__line">{v.line}</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <p className="mc-stage__claim" aria-hidden="true">
            Real solutions
            <br />
            for a tougher
            <br />
            tomorrow
          </p>

          <div className="mc-collection">
            <p className="mc-collection__count">
              The European range <span aria-hidden="true">·</span> {MACHINES.length} machines{' '}
              <span aria-hidden="true">·</span> {VISUAL_CATEGORIES.length} categories
            </p>
            <ul className="mc-collection__floor">
              {pieces.map((category, i) => (
                <li className="mc-collection__slot" data-slot={i + 1} key={category.id}>
                  <CategoryPiece category={category} front={i >= 4} onOpen={onOpen} />
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
      <LandcrosBand />
    </>
  )
}

interface CategoryPieceProps {
  category: Category
  front: boolean
  onOpen: (id: string) => void
}

/**
 * One category: the machine on its podium, its name, a line, and the cue.
 *
 * No card and no border at rest - the machine stands on a white disc. On hover
 * or focus the piece lifts into a soft glowing panel, the podium warms orange
 * and the arrow fills; the whole piece is the target.
 */
function CategoryPiece({ category, front, onOpen }: CategoryPieceProps) {
  return (
    <button
      className={`mc-piece${front ? ' mc-piece--front' : ''}`}
      type="button"
      onClick={() => onOpen(category.id)}
    >
      <span className="mc-piece__stage">
        <span className="mc-piece__plinth" aria-hidden="true" />
        <MachineImage
          image={category.heroImage}
          alt={`${category.label} — ${category.heroMachine || 'Hitachi machine'}`}
          cutout={category.heroIsCutout}
          /* Eager: these seven are the section, and lazy loading once failed
             to fire for one of them and left a broken image in its place. */
          priority
          sizes="(max-width: 700px) 72vw, (max-width: 1100px) 30vw, 22vw"
          className={`mc-piece__img${category.heroIsCutout ? '' : ' mc-piece__img--masked'}`}
        />
      </span>
      <span className="mc-piece__label">{category.label}</span>
      <span className="mc-piece__blurb">{category.blurbShort || category.blurb}</span>
      <span className="mc-piece__cue" aria-hidden="true">
        →
      </span>
    </button>
  )
}

/* --------------------------------------------------------------- detail ---- */

interface MachineDetailProps {
  machine: Machine
  category: Category | null
  onBack: () => void
}

/**
 * The machine detail shell.
 *
 * Deliberately a shell. This pass is validating that the navigation holds, so
 * Parts, Service and the digital services are named as what comes next rather
 * than built. What IS here is real: every fact and every photograph comes from
 * the data foundation.
 */
function MachineDetail({ machine, category, onBack }: MachineDetailProps) {
  const gallery = machine.images.slice(1, 7)
  const facts: [string, string | undefined][] = (
    [
      ['Category', categoryTitle(category)],
      ['Machine type', machine.machineType],
      ['Power type', machine.powerType],
      ['Operating weight', machine.operatingWeight],
      ['Engine / motor power', machine.power],
    ] as [string, string | undefined][]
  ).filter(([, v]) => v && v !== 'NOT PUBLICLY STATED')

  return (
    <div className="mc__detail">
      <button className="mc__backtop" type="button" onClick={onBack}>
        <span aria-hidden="true">←</span> All {categoryTitle(category)}
      </button>

      <div className="mc__lede">
        <p className="mc__eyebrow">{categoryTitle(category)}</p>
        <h2 className="mc__title" id="mc-title">
          {machine.name}
        </h2>
        {machine.modelCount > 1 && (
          <p className="mc__sub">
            This official product page covers {machine.modelCount} model codes:{' '}
            {machine.modelsCovered.join(' · ')}.
          </p>
        )}
      </div>

      <div className="mc__hero">
        <MachineImage
          image={machine.images[0]}
          alt={machine.name}
          priority
          sizes="(max-width: 900px) 92vw, 70vw"
          className="mc__hero-img"
        />
      </div>

      <div className="mc__detail-body">
        <div className="mc__facts">
          <h3 className="mc__h3">Machine</h3>
          <dl className="mc__dl">
            {facts.map(([k, v]) => (
              <div className="mc__dl-row" key={k}>
                <dt>{k}</dt>
                <dd>{v}</dd>
              </div>
            ))}
          </dl>
          {machine.application && (
            <>
              <h3 className="mc__h3">Applications</h3>
              <p className="mc__body">{machine.application}</p>
            </>
          )}
          <a className="mc__source" href={machine.sourceUrl} target="_blank" rel="noreferrer">
            Official Hitachi product page <span aria-hidden="true">↗</span>
          </a>
        </div>

        <div className="mc__next">
          <h3 className="mc__h3">After-sales</h3>
          <ul className="mc__next-list">
            <li>Parts that fit this machine</li>
            <li>Attachments it supports</li>
            <li>Service that applies to it</li>
            <li>Digital services that support it</li>
          </ul>
          <p className="mc__note">
            The data foundation already holds all four for this machine. They are not wired
            into the screen yet — this pass is the machine universe and how you move through it.
          </p>
        </div>
      </div>

      {gallery.length > 0 && (
        <div className="mc__gallery">
          <h3 className="mc__h3">Gallery</h3>
          <div className="mc__gallery-grid">
            {gallery.map((img) => (
              <figure className="mc__shot" key={img.src}>
                <MachineImage
                  image={img}
                  alt={machine.name}
                  sizes="(max-width: 900px) 45vw, 240px"
                  className="mc__shot-img"
                />
              </figure>
            ))}
          </div>
        </div>
      )}

      <button className="mc__back" type="button" onClick={onBack}>
        <span aria-hidden="true">←</span> All {categoryTitle(category)}
      </button>
    </div>
  )
}
