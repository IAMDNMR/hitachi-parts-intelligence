import { useState, type FormEvent } from 'react'

interface Stage2RequesterProps {
  name: string
  email: string
  company?: string
  onChangeName: (val: string) => void
  onChangeEmail: (val: string) => void
  onChangeCompany?: (val: string) => void
  onBack: () => void
  onNext: () => void
}

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export default function Stage2Requester({
  name,
  email,
  company = '',
  onChangeName,
  onChangeEmail,
  onChangeCompany,
  onBack,
  onNext,
}: Stage2RequesterProps) {
  const [touched, setTouched] = useState({ name: false, email: false })

  const isNameValid = name.trim().length >= 2
  const isEmailValid = EMAIL_REGEX.test(email.trim())
  const canProceed = isNameValid && isEmailValid

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    setTouched({ name: true, email: true })
    if (canProceed) {
      onNext()
    }
  }

  return (
    <div className="cw-stage">
      <div className="cw-stage__header">
        <div className="cw-stage__badge cw-stage__badge--info">IDENTITY &amp; AUDIT TRAIL</div>
        <h3 className="cw-stage__title">2. Requester Information</h3>
        <p className="cw-stage__desc">
          Specify who is requesting this parts fulfilment. Requester identity is persisted to the Neo4j graph audit trail.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="cw-form">
        <div className="cw-field-group">
          <div className="cw-field">
            <label htmlFor="requester-name">
              Full Name <span className="cw-required">*</span>
            </label>
            <input
              id="requester-name"
              type="text"
              placeholder="e.g. Johannes van der Berg"
              value={name}
              onChange={(e) => onChangeName(e.target.value)}
              onBlur={() => setTouched((prev) => ({ ...prev, name: true }))}
              required
              className={touched.name && !isNameValid ? 'cw-input--error' : ''}
            />
            {touched.name && !isNameValid && (
              <span className="cw-error-msg">Please enter a valid contact name (at least 2 characters).</span>
            )}
          </div>

          <div className="cw-field">
            <label htmlFor="requester-email">
              Business Email <span className="cw-required">*</span>
            </label>
            <input
              id="requester-email"
              type="email"
              placeholder="e.g. j.vanderberg@fleet-services.nl"
              value={email}
              onChange={(e) => onChangeEmail(e.target.value)}
              onBlur={() => setTouched((prev) => ({ ...prev, email: true }))}
              required
              className={touched.email && !isEmailValid ? 'cw-input--error' : ''}
            />
            {touched.email && !isEmailValid && (
              <span className="cw-error-msg">Please enter a valid email address.</span>
            )}
          </div>
        </div>

        <div className="cw-field">
          <label htmlFor="requester-company">Company / Fleet Customer (Optional)</label>
          <input
            id="requester-company"
            type="text"
            placeholder="e.g. EuroPlant Heavy Operations B.V."
            value={company}
            onChange={(e) => onChangeCompany?.(e.target.value)}
          />
        </div>

        <div className="cw-notice cw-notice--info">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="16" x2="12" y2="12" />
            <line x1="12" y1="8" x2="12.01" y2="8" />
          </svg>
          <div>
            <strong>Identity Persistence:</strong> A <code>Customer</code> node is matched or created in Neo4j with
            relationship <code>(:Customer)-[:REQUESTED]-&gt;(:FulfilmentRequest)</code>.
          </div>
        </div>

        <div className="cw-actions">
          <button type="button" className="cw-btn cw-btn--secondary" onClick={onBack}>
            ← Back to Cart
          </button>
          <button type="submit" className="cw-btn cw-btn--primary" disabled={!canProceed}>
            Next: Destination Dealer →
          </button>
        </div>
      </form>
    </div>
  )
}
