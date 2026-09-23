// Channel — 2 distinct values, sourced from relationships.csv (there is no
// dedicated channel sheet). Approved decision: keep as a node.
//
// REVISED after final pre-import review (see
// neo4j/FINAL_PRE_IMPORT_REVIEW.md item 2). The previous version set
// Channel.label directly from each row's "To Name" text. Direct inspection
// found CH-DEALER's "To Name" is stable across every row ("HCME authorised
// dealer network"), but CH-EXTERNAL's varies by which service references it
// ("Yes (Reman centre)" for SVC-016; "Yes (BNP Paribas Leasing Solutions;
// DLL)" for SVC-022) — because that text answers a PER-SERVICE question
// ("who is the external provider for THIS service?"), not a fixed identity
// for the Channel itself. Reading whichever row happened to load first as if
// it were the channel's universal label was a graph-design error on the
// previous pass, not a source data problem — the source data is fine; it was
// being read into the wrong place in the schema. The per-service detail now
// moves to the DELIVERED_BY relationship (see relationships/
// channel_relationships.cypher), which is where a fact that varies by
// (Service, Channel) pair belongs.
//
// Still driven from the CSV (not hardcoded), so a genuinely new Channel ID
// appearing in a future data refresh is still created rather than silently
// dropped — it just gets label = null (needing a human labelling decision)
// instead of an arbitrary, possibly-wrong "To Name" value.
LOAD CSV WITH HEADERS FROM 'file:///relationships.csv' AS row
WITH row WHERE row.`To Entity Type` = 'Channel'
WITH DISTINCT row.`To ID` AS channel_id
MERGE (c:Channel {channel_id: channel_id})
SET c.label = CASE channel_id
    WHEN 'CH-DEALER' THEN 'HCME authorised dealer network'
    WHEN 'CH-EXTERNAL' THEN 'External authorised provider (varies by service — see provider_detail on each DELIVERED_BY relationship)'
    ELSE null // any future, currently-unseen channel id: flagged via a null label rather than guessed at
END;
