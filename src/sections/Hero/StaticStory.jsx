import posterFrame from '../../../assets/source/section-01/hero-frames/frame-001.webp'
import finalFrame from '../../../assets/source/section-01/hero-frames/frame-090.webp'
import { storyStates } from '../../data/storyStates'
import { MACHINE_ID } from '../../data/machineData'
import { ecosystemNodes } from '../../data/ecosystemNodes'
import { journeySteps } from '../../data/journey'
import { NodeIcon, ArrowRight } from './Icons'

/**
 * The reduced-motion telling of the same story.
 *
 * No scrubbing, no pinning, no video: representative still frames and the
 * complete text, in reading order. Everything the scrolled version reveals
 * over time is present here at once.
 */
export function StaticStory({ onOpenNode, onExplore }) {
  return (
    <div className="static">
      {storyStates.map((state) => (
        <section
          className="static__chapter"
          key={state.id}
          /* Namespaced: the bare chapter ids collide with the
             section anchors further down the page — Section 05 also
             uses id="uptime". */
          id={`chapter-${state.id}`}
        >
          <p className="story__eyebrow">{state.eyebrow}</p>
          <h2 className="story__heading">
            {state.heading.map((line) => (
              <span key={line}>{line}</span>
            ))}
          </h2>
          <p className="story__body">{state.body}</p>

          {state.id === 'machine' && (
            <figure className="static__figure">
              <img
                src={posterFrame}
                alt="A complete Hitachi hydraulic excavator, ready for delivery."
                width="1280"
                height="720"
              />
            </figure>
          )}

          {state.showMachineState && (
            <p className="machine-id machine-id--static">
              <span className="machine-id__label">{MACHINE_ID.label}</span>
              <span className="machine-id__value">{MACHINE_ID.value}</span>
            </p>
          )}

          {state.id === 'ecosystem' && (
            <>
              <figure className="static__figure">
                <img
                  src={finalFrame}
                  alt="The same excavator separated into its major components: boom and arm, operator cab, undercarriage, upper structure, hydraulic pump and final drive."
                  width="1280"
                  height="720"
                />
              </figure>
              <div className="static__cards">
                {ecosystemNodes.map((node) => (
                  <button
                    type="button"
                    className="card"
                    key={node.id}
                    onClick={() => onOpenNode(node.id)}
                  >
                    <span className="card__icon">
                      <NodeIcon name={node.icon} />
                    </span>
                    <span className="card__text">
                      <span className="card__label">{node.label}</span>
                      <span className="card__component">{node.component}</span>
                    </span>
                  </button>
                ))}
              </div>
            </>
          )}

          {state.showJourney && (
            <ol className="static__journey">
              {journeySteps.map((step) => (
                <li key={step.id}>{step.label}</li>
              ))}
            </ol>
          )}

          {state.cta && (
            <a
              className="cta"
              href={state.cta.href}
              onClick={(event) => {
                event.preventDefault()
                onExplore()
              }}
            >
              {state.cta.label}
              <ArrowRight />
            </a>
          )}
        </section>
      ))}
    </div>
  )
}
