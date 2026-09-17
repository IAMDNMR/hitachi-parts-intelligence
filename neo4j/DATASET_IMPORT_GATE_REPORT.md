# Dataset Import Gate Report

Triggered by a count discrepancy between a report produced by a separate agent ("Antigravity," operating on this same repository in parallel) and the previously-approved cleaned dataset. No import was run. No write Cypher was executed. This report is read-only investigation output.

## 1. Approved dataset counts

(As established across the cleaning, schema-review, and final pre-import-review phases, and re-confirmed multiple times this session.)

| Dataset | Approved count |
|---|---|
| Categories | 17 |
| Machines | 77 |
| Specifications | 1635 |
| Applications | 328 (29 distinct) |
| Attachments | 17 |
| Parts | 43 (20 ORDERABLE_OEM_PART / 23 PRODUCT_LINE_PART_FAMILY) |
| Machine-Part Fitment | 944 source rows (943 valid graph relationships, 1 excluded sentinel — see `FITMENT_COUNT_RECONCILIATION.md`) |
| Services | 22 |
| Machine-Service | 1694 |
| Maintenance | 10 |
| Service-Part Requirements | 11 |
| Digital Services | 616 rows / 8 distinct |
| Relationships (sheet 13) | 3283 (186 CORE / 3097 DERIVED) |
| Provenance | 47 |

## 2. Current CSV counts (independently re-verified this task, by direct row count on the files actually present in `neo4j/data/`)

| Dataset | Current count | Matches approved? |
|---|---|---|
| Categories | 17 | Yes |
| Machines | 77 | Yes |
| Specifications | 1635 | Yes |
| Applications | 328 | Yes |
| Attachments | 17 | Yes |
| Parts | 43 | Yes |
| Machine-Part Fitment | 944 | Yes |
| Services | 22 | Yes |
| Machine-Service | 1694 | Yes |
| Maintenance | 10 | Yes |
| Service-Part Requirements | 11 | Yes |
| Digital Services | 616 | Yes |
| Relationships | 3283 | Yes |
| Provenance | 47 | Yes |

**Every current count exactly matches the approved baseline.** All 14 files under `neo4j/data/` carry the unchanged timestamp `Sep 17 13:18`, the same timestamp captured at the end of the final pre-import review, before Antigravity's report was produced. `HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx` likewise carries that same unchanged timestamp.

## 3. Every discrepancy

The discrepancy is entirely between Antigravity's reported numbers and the real files — not between two versions of the real files:

| Dataset | Antigravity reported | Actual on disk | Discrepancy |
|---|---|---|---|
| Specifications | 884 | 1635 | 751 fewer than actual |
| Applications | 267 | 328 | 61 fewer than actual |
| Parts | 39 | 43 | 4 fewer than actual |
| Machine-Part Fitment | 1607 | 944 | 663 more than actual |
| Maintenance | 12 | 10 | 2 more than actual |
| Relationships | 3284 | 3283 | 1 more than actual |
| Provenance | 48 | 47 | 1 more than actual |

No pattern here (some numbers lower, some higher, by inconsistent margins) is consistent with a single coherent alternative interpretation, such as "pre-deduplication counts" or "a different but valid grain of aggregation" — a real methodological difference would typically move every count in one consistent direction or by an explicable, uniform transformation. This inconsistency is itself evidence against Antigravity's numbers representing a legitimate alternative view of the same data.

## 4. Root cause

**Not fully determinable from this task, and not guessed at.** I did not observe Antigravity's process, script, or intermediate data — only its final chat output. What I can state with certainty, from direct, independent verification (row counts and file timestamps against the actual files in `neo4j/data/` and the actual `HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx`):

- The real files on disk are unchanged since the final pre-import review (identical counts, identical timestamps).
- Antigravity's reported counts do not correspond to the current state of any file in `neo4j/data/`.
- This matches a pattern already observed once earlier in this project: a separate, independently-running agent operating on the same directory produced a fabricated/incorrect audit of the same source data (documented in the original cleaning-phase work). This appears to be a recurrence of the same failure mode, not a new data problem.

## 5. Which dataset is authoritative

**The CSVs currently in `neo4j/data/` and `HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx`** — verified directly, matching every previously-documented and independently-reconciled count from this session's cleaning, schema-review, model-code-reconciliation, and final-pre-import-review phases. Antigravity's report is not authoritative for this dataset.

## 6. Whether any CSV must be regenerated

**No.** The existing CSVs are correct, unmodified, and already the ones the entire approved import design (`neo4j/import/`) was built against.

## 7. Whether the import Cypher must change

**No.** Nothing about this investigation changes any finding from `neo4j/FINAL_PRE_IMPORT_REVIEW.md`. The import Cypher under `neo4j/import/` remains as previously reviewed and approved.

## 8. Aura database state

**Not independently re-verified by me in this task.** Running even a read-only Cypher query against Aura requires authenticating with the credential now sitting in `neo4j/.env` — I'm not reading or using that value, for the same reason described in §9 below, so I have no fresh, first-hand confirmation of the current node/relationship counts.

The most recent evidence available is your own screenshot of the Aura browser console (from earlier in this session) showing "No data found in the connected instance," which is consistent with an empty database. To get a current, first-hand read, please run the following directly in Aura's own Query console (you're already authenticated there — no credential needs to move through me or this repo):

```cypher
MATCH (n) RETURN count(n) AS nodes;
MATCH ()-[r]->() RETURN count(r) AS relationships;
```

Expected: `nodes = 0`, `relationships = 0`.

## 9. Credential-security status

- `neo4j/.env` exists on disk (created by Antigravity) and contains the Aura username and password in plaintext.
- Verified: `neo4j/.env` **is** correctly matched by `.gitignore` (`neo4j/.env` and `**/.env` are both listed) and does **not** appear as trackable in `git status` — it has not been committed.
- However, this password has now appeared in this chat transcript multiple times via screenshot, independent of the `.env` file. **Recommend rotating the Aura password before proceeding with any import**, regardless of the file's git-ignored status, since a value that has passed through a chat transcript should be treated as no longer private.
- I have not read, displayed, logged, or used this credential at any point, and will not until you've rotated it and there is a channel for it that doesn't require me to handle it in plain text (see the credential-handling discussion earlier in this session).

## 10. Final decision

**DATASET_RECONCILED_READY_FOR_IMPORT**

The dataset itself has no real discrepancy — the numbers in `neo4j/data/` and `HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx` match the approved baseline exactly, verified independently. The apparent mismatch originated entirely from a different agent's report, not from any change to the actual files.

This dataset-readiness verdict is **separate from** two outstanding action items that should be resolved before an actual Aura import proceeds:
1. Rotate the Aura password (per §9) — it has been exposed in chat multiple times.
2. Independently confirm Aura is still empty via Aura's own console (per §8) — the only evidence of this I have is not first-hand from this task.

No data was imported. No write Cypher was run. No credential was read, displayed, or used.
