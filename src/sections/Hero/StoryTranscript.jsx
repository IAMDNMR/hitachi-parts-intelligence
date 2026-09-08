import { storyStates } from '../../data/storyStates'
import { MACHINE_ID } from '../../data/machineData'
import { ecosystemNodes } from '../../data/ecosystemNodes'
import { journeySteps } from '../../data/journey'

/**
 * A plain-text telling of the scrolled story, for assistive technology.
 *
 * The scrolled hero conveys its meaning through timing and motion, which does
 * not survive being read aloud — so the same content is also present here as
 * ordinary prose. No interactive elements: the visible hero already provides
 * those, and duplicating them would double every control in the a11y tree.
 */
export function StoryTranscript() {
  return (
    <div className="visually-hidden">
      <h2>What happens after a Hitachi machine is sold</h2>
      <p>
        An animated sequence shows a Hitachi hydraulic excavator that
        progressively separates into its major components — boom and arm,
        operator cab, undercarriage, upper structure, hydraulic pump and final
        drive — and then comes back together as the story below unfolds.
      </p>

      {storyStates.map((state) => (
        <section key={state.id}>
          <h3>
            {state.eyebrow} — {state.heading.join(' ')}
          </h3>
          <p>{state.body}</p>

          {state.showMachineState && (
            <p>
              {MACHINE_ID.label}: {MACHINE_ID.value}
            </p>
          )}

          {state.id === 'ecosystem' && (
            <>
              <p>The six after-sales domains:</p>
              <ul>
                {ecosystemNodes.map((node) => (
                  <li key={node.id}>
                    {node.panel.title}, from the {node.component.toLowerCase()} —{' '}
                    {node.panel.lead}
                  </li>
                ))}
              </ul>
            </>
          )}

          {state.showJourney && (
            <>
              <p>The after-sales route, from issue to uptime:</p>
              <ol>
                {journeySteps.map((step) => (
                  <li key={step.id}>{step.label}</li>
                ))}
              </ol>
            </>
          )}
        </section>
      ))}
    </div>
  )
}
