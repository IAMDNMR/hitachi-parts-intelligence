import { submitQuoteRequest } from './_lib/quoteRequest.js'

function isNonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

/**
 * POST /api/quote-request — the only write path in this project's API
 * layer that a site visitor can trigger. Name, email and phone are
 * required (note is not) — the same rule the form itself enforces
 * (PartsStore.jsx's validateQuoteDetails); checked again here since a
 * request can reach this endpoint without going through that form. Beyond
 * "present and email-shaped", nothing about a customer detail is verified,
 * invented, or backfilled — whatever the visitor typed is what gets stored.
 */
export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Method not allowed' })
    return
  }

  const { name, email, phone, note, items } = req.body || {}

  if (!isNonEmptyString(name) || !isNonEmptyString(email) || !isNonEmptyString(phone)) {
    res.status(400).json({ error: 'Name, email and phone are required.' })
    return
  }
  if (!EMAIL_PATTERN.test(email.trim())) {
    res.status(400).json({ error: 'Enter a valid email address.' })
    return
  }
  if (!Array.isArray(items) || items.length === 0) {
    res.status(400).json({ error: 'At least one part is required.' })
    return
  }

  try {
    const result = await submitQuoteRequest({
      name: name.trim(),
      email: email.trim(),
      phone: phone.trim(),
      note: isNonEmptyString(note) ? note.trim() : null,
      items,
    })
    res.status(200).json({ ok: true, ...result })
  } catch (error) {
    console.error('POST /api/quote-request failed:', error.message)
    res.status(502).json({ error: "We couldn't send your request right now. Please try again." })
  }
}
