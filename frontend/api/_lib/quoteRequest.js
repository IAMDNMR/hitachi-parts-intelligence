import { randomUUID } from 'node:crypto'
import { withWriteSession } from './neo4j.js'

/**
 * Writes one customer inquiry into Neo4j as:
 *
 *   (:PartsInquiry)-[:REQUESTS]->(:RequestedPart)-[:FOR_PART]->(:Part)
 *
 * PartsInquiry carries the customer's own submitted details and a
 * server-generated timestamp — never invented. RequestedPart is one node
 * per cart line, carrying exactly what the site's cart already held for it
 * (name, quantity) — not re-derived or guessed. FOR_PART links to a real
 * Part node only when the cart line's partNumber matches one; a cart item
 * with no partNumber (most of the original showcase parts, which predate
 * the workbook import) still gets its RequestedPart node, just without a
 * FOR_PART edge — an honest gap, not a fabricated link to the wrong part or
 * to none at all silently.
 */
export async function submitQuoteRequest({ name, email, phone, note, items }) {
  const inquiryId = randomUUID()

  return withWriteSession((session) =>
    session.executeWrite((tx) =>
      tx.run(
        `
        CREATE (i:PartsInquiry {
          inquiry_id: $inquiryId,
          name: $name,
          email: $email,
          phone: $phone,
          note: $note,
          created_at: datetime()
        })
        WITH i
        UNWIND $items AS item
        CREATE (rp:RequestedPart {
          requested_part_id: item.requestedPartId,
          part_id: item.id,
          part_name: item.name,
          quantity: item.qty,
          machine: item.machine
        })
        CREATE (i)-[:REQUESTS]->(rp)
        WITH i, rp, item
        OPTIONAL MATCH (p:Part {part_number: item.partNumber})
        FOREACH (_ IN CASE WHEN item.partNumber IS NOT NULL AND p IS NOT NULL THEN [1] ELSE [] END |
          CREATE (rp)-[:FOR_PART]->(p)
        )
        RETURN i.inquiry_id AS inquiryId, count(rp) AS requestedPartCount
        `,
        {
          inquiryId,
          name,
          email,
          phone: phone || null,
          note: note || null,
          items: items.map((item, index) => ({
            requestedPartId: `${inquiryId}-${index}`,
            id: item.id ?? null,
            name: item.name,
            qty: item.qty,
            machine: item.machine ?? null,
            partNumber: item.partNumber ?? null,
          })),
        },
      ),
    ),
  ).then((result) => {
    const record = result.records[0]
    return {
      inquiryId: record.get('inquiryId'),
      requestedPartCount: record.get('requestedPartCount').toNumber(),
    }
  })
}
