# Schema Candidates

Node candidates, each with the evidence behind it. No node type is added automatically —
this is for review before any Neo4j schema is created.

| Candidate | Source sheet | Records | Recommendation |
|---|---|---|---|
| Category | 01_MACHINE_CATEGORIES | 17 | Node — is the hierarchy root, has its own ID and CHILD_OF structure via Parent Category. |
| Machine | 02_MACHINE_MASTER | 77 | Node — the central entity everything else attaches to. |
| Specification | 03_MACHINE_SPECIFICATIONS | 1635 | Property-bag candidate: could be a node (Spec ID exists) or a property set on Machine. Recommend node — EAV shape (Specification Name/Value/Unit) does not fit as flat Machine properties. |
| Application | 04_MACHINE_APPLICATIONS | 29 | Node — reused across many machines, canonical name after normalization. |
| Part | 06_PART_MASTER | 43 | Node — split by record_class (ORDERABLE_OEM_PART vs PRODUCT_LINE_PART_FAMILY), both real distinct concepts. |
| Attachment | 05_ATTACHMENTS | 17 | Node — many-to-many with Machine, has its own ID. |
| Service | 08_SERVICE_CAPABILITIES | 22 | Node — reused across the machine-service matrix. |
| DigitalService | 12_MACHINE_DIGITAL_SERVICES | 616 | Node — distinct from Service (different capability set, different source sheet). |
| MaintenanceActivity | 10_MAINTENANCE_SCHEDULE | 10 | Only 10 rows and mostly NOT PUBLICLY STATED. Recommend: property on a Machine-Service edge rather than its own node, pending more data. |
| Source | 14_SOURCE_REGISTER | 47 | Node candidate for provenance, or a compact property set (source_id, source_name, confidence) on each fact — recommend property set per the "no URL blast radius" requirement, not a node customers would ever traverse. |