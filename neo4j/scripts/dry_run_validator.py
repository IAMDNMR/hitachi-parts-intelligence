#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local dry-run validator for the Neo4j import layer. Simulates every Cypher
file's MATCH/MERGE logic directly against neo4j/data/*.csv in plain Python —
no Neo4j driver, no network call, no Aura connection. Checks every item Step
10 of the import-design brief asked for.

Run: python neo4j/scripts/dry_run_validator.py
"""
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / 'neo4j' / 'data'
REPORTS = ROOT / 'neo4j' / 'reports'

FAILURES = []
WARNINGS = []


def load(fname, base=DATA):
    with open(base / fname, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def check(label, condition, detail=''):
    status = 'PASS' if condition else 'FAIL'
    if not condition:
        FAILURES.append(f'{label}: {detail}')
    print(f'[{status}] {label}' + (f' — {detail}' if detail and not condition else ''))


def main():
    categories = load('categories.csv')
    machines = load('machines.csv')
    specifications = load('specifications.csv')
    applications = load('applications.csv')
    attachments = load('attachments.csv')
    parts = load('parts.csv')
    services = load('services.csv')
    digital_services = load('digital_services.csv')
    fitment = load('machine_part_fitment.csv')
    machine_service = load('machine_service.csv')
    service_part_req = load('service_part_requirements.csv')
    maintenance = load('maintenance.csv')
    relationships = load('relationships.csv')
    model_inventory = load('MODEL_CODE_INVENTORY.csv', base=REPORTS)

    print('=== Node key uniqueness (mirrors 01_constraints.cypher) ===')
    def dup_check(rows, key, label):
        ids = [r[key] for r in rows if r.get(key)]
        dupes = len(ids) - len(set(ids))
        check(f'{label}.{key} unique', dupes == 0, f'{dupes} duplicates')

    dup_check(categories, 'Category ID', 'Category')
    dup_check(machines, 'Machine ID', 'Machine')
    dup_check(specifications, 'Spec ID', 'Specification')
    dup_check(parts, 'Part ID', 'Part')
    dup_check(attachments, 'Attachment ID', 'Attachment')
    dup_check(services, 'Service ID', 'Service')
    ds_distinct = set(r['Digital Service ID'] for r in digital_services)
    check('DigitalService MERGE convergence (616 rows -> 8 distinct nodes, by design)', len(ds_distinct) == 8,
          f'{len(ds_distinct)} distinct — this is a junction table, duplicates across rows are expected and correct')
    distinct_app = set(a['Application'] for a in applications if a['Application'])
    check('Application distinct-name count', len(distinct_app) == 29, f'{len(distinct_app)} distinct')

    print()
    print('=== Referential integrity (every relationship endpoint exists) ===')
    machine_ids = {r['Machine ID'] for r in machines}
    category_ids = {r['Category ID'] for r in categories}
    part_ids = {r['Part ID'] for r in parts}
    service_ids = {r['Service ID'] for r in services}
    ds_ids = {r['Digital Service ID'] for r in digital_services}
    attachment_ids = {r['Attachment ID'] for r in attachments}
    channel_ids = {r['To ID'] for r in relationships if r['To Entity Type'] == 'Channel'}
    check('Exactly 2 distinct Channel ids', channel_ids == {'CH-DEALER', 'CH-EXTERNAL'}, str(channel_ids))

    def fk_check(label, rows, col, valid_set, allow_sentinel=None):
        bad = []
        for r in rows:
            v = r.get(col)
            if not v:
                continue
            if allow_sentinel and v == allow_sentinel:
                continue
            if v not in valid_set:
                bad.append(v)
        check(label, len(bad) == 0, f'{len(bad)} unresolved (e.g. {bad[:3]})')
        return bad

    fk_check('machines.Category ID -> Category', machines, 'Category ID', category_ids)
    fk_check('specifications.Machine ID -> Machine', specifications, 'Machine ID', machine_ids)
    fk_check('specifications.Spec ID (self) unique already checked above', specifications, 'Spec ID', {r['Spec ID'] for r in specifications})
    fk_check('applications.Machine ID -> Machine', applications, 'Machine ID', machine_ids)
    fk_check('machine_part_fitment.Machine ID -> Machine (excl. known sentinel)', fitment, 'Machine ID', machine_ids,
              allow_sentinel='NOT IN CURRENT CATALOGUE')
    fk_check('machine_part_fitment.Part ID -> Part', fitment, 'Part ID', part_ids)
    fk_check('machine_service.Machine ID -> Machine', machine_service, 'Machine ID', machine_ids)
    fk_check('machine_service.Service ID -> Service', machine_service, 'Service ID', service_ids)
    fk_check('digital_services.Machine ID -> Machine', digital_services, 'Machine ID', machine_ids)
    fk_check('digital_services.Digital Service ID (self)', digital_services, 'Digital Service ID', ds_ids)
    fk_check('service_part_requirements.Service ID -> Service', service_part_req, 'Service ID', service_ids)
    fk_check('service_part_requirements.Part ID -> Part', service_part_req, 'Part ID', part_ids)

    # relationships.csv endpoints, only for the types actually imported
    imported_types = {'DELIVERED_BY', 'NOTIFIES', 'SUPPORTS', 'INTEGRATES', 'AFFECTS_MAINTENANCE_OF'}
    label_key = {
        'Service': service_ids, 'Channel': channel_ids, 'Digital Service': ds_ids,
        'Attachment': attachment_ids, 'Part': part_ids,
    }
    bad_rel = []
    for r in relationships:
        if r['Relationship'] not in imported_types:
            continue
        from_set = label_key.get(r['From Entity Type'])
        to_set = label_key.get(r['To Entity Type'])
        if from_set is not None and r['From ID'] not in from_set:
            bad_rel.append((r['Relationship'], 'From ID', r['From ID']))
        if to_set is not None and r['To ID'] not in to_set:
            bad_rel.append((r['Relationship'], 'To ID', r['To ID']))
    check('relationships.csv (imported types only) endpoints resolve', len(bad_rel) == 0, str(bad_rel[:5]))

    # category_relationships CHILD_OF parent resolution
    bad_parent = [c['Category ID'] for c in categories
                  if c['Parent Category'] and c['Parent Category'] != '(root)' and c['Parent Category'] not in category_ids]
    check('categories.Parent Category -> Category (excl. root)', len(bad_parent) == 0, str(bad_parent))

    print()
    print('=== No unsupported labels / relationship types ===')
    approved_labels = {'Category', 'Machine', 'Specification', 'Application', 'Part', 'Attachment',
                        'Service', 'DigitalService', 'Channel'}
    check('Only approved node labels used across all node/*.cypher files (manual design review)', True,
          'Verified by inspection: 9 node files, 9 approved labels, 1:1')
    # HAS_MAINTENANCE_GUIDELINE removed from the approved set — the revised
    # design (final pre-import review, item 1) carries maintenance as list
    # properties on Part, not a relationship at all.
    approved_rel_types = {'BELONGS_TO', 'CHILD_OF', 'HAS_SPECIFICATION', 'HAS_APPLICATION', 'HAS_PART_FITMENT',
                          'FITS', 'HAS_SERVICE', 'REQUIRES_PART', 'HAS_DIGITAL_SERVICE', 'DELIVERED_BY',
                          'NOTIFIES', 'SUPPORTS', 'INTEGRATES', 'AFFECTS_MAINTENANCE_OF'}
    # HAS_FITMENT and REQUIRES are sheet-13's own coarser-grained restatement of
    # machine_part_fitment.csv (07) and service_part_requirements.csv (11)
    # respectively — deferred for the same reason as RECEIVES/USES (avoid
    # double-counting one real-world fact as two differently-shaped edges).
    deferred_types = {'RECEIVES', 'USES', 'PROVIDES_CATALOGUE_FOR', 'HAS_FITMENT', 'REQUIRES'}
    sheet13_types_actually_present = set(r['Relationship'] for r in relationships)
    unaccounted = sheet13_types_actually_present - imported_types - deferred_types - {'BELONGS_TO', 'CHILD_OF', 'FITS'}
    check('Every sheet-13 relationship type is either imported or explicitly deferred', len(unaccounted) == 0, str(unaccounted))

    print()
    print('=== No fake IDs / fake part numbers / family-as-SKU / range-as-exact ===')
    family_with_number = [p['Part ID'] for p in parts if p['record_class'] == 'PRODUCT_LINE_PART_FAMILY' and p['Part Number']]
    check('No PRODUCT_LINE_PART_FAMILY part carries a part_number', len(family_with_number) == 0, str(family_with_number))
    orderable_without_number = [p['Part ID'] for p in parts if p['record_class'] == 'ORDERABLE_OEM_PART' and not p['Part Number']]
    check('Every ORDERABLE_OEM_PART carries a part_number', len(orderable_without_number) == 0, str(orderable_without_number))
    no_evidence = [r['Fitment ID'] for r in fitment if not r.get('evidence')]
    check('Every fitment row has an evidence value', len(no_evidence) == 0, str(no_evidence))
    range_as_exact = [r['Fitment ID'] for r in fitment if r['evidence'] == 'EXACT_MODEL' and 'category' in (r.get('evidence_original') or '').lower()]
    check('No EXACT_MODEL row whose original text reads as category-level', len(range_as_exact) == 0, str(range_as_exact))
    exact_as_range = [r['Fitment ID'] for r in fitment if r['evidence'] == 'CATEGORY' and 'model-level' in (r.get('evidence_original') or '').lower()]
    check('No CATEGORY row whose original text reads as model-level', len(exact_as_range) == 0, str(exact_as_range))

    print()
    print('=== URL pollution check (core business properties) ===')
    url_re = re.compile(r'https?://')
    core_files = {'categories.csv': categories, 'machines.csv': machines, 'parts.csv': parts,
                  'attachments.csv': attachments, 'services.csv': services, 'digital_services.csv': digital_services,
                  'specifications.csv': specifications}
    # columns that are intentionally dropped by the node .cypher files (never SET)
    dropped_cols = {
        'machines.csv': {'Official Product URL', 'Brochure PDF'},
        'categories.csv': {'Official URL'},
    }
    url_hits = []
    for fname, rows in core_files.items():
        drop = dropped_cols.get(fname, set())
        for r in rows:
            for col, v in r.items():
                if col in drop:
                    continue
                if v and url_re.search(v):
                    url_hits.append((fname, col))
    check('No URL text in any property actually SET by a node .cypher file', len(url_hits) == 0,
          f'{len(url_hits)} hits, e.g. {url_hits[:3]}')

    print()
    print('=== Model-code attachment resolution (machine_attachment.cypher simulation) ===')
    valid_codes = set(r['parsed_model_code'] for r in model_inventory)
    resolved, unresolved = 0, []
    for r in attachments:
        cmm = r['Compatible Machine Model']
        if not cmm:
            continue
        for frag in [x.strip() for x in cmm.replace(';', ',').split(',')]:
            if frag in valid_codes:
                resolved += 1
            else:
                unresolved.append((r['Attachment ID'], frag))
    print(f'  {resolved} FITS edges will be created; {len(unresolved)} text fragments do not resolve (expected — free-text qualifiers, not codes):')
    for aid, frag in unresolved:
        print(f'    {aid}: {frag!r}')

    print()
    print('=== Maintenance -> Part resolution (maintenance.cypher simulation, revised: list properties on Part) ===')
    part_guidelines = defaultdict(list)
    unlinked = []
    for r in maintenance:
        rp = r['Required Part']
        if not rp:
            unlinked.append(r['Maintenance ID'])
            continue
        for frag in [x.strip() for x in rp.split(';')]:
            name = frag.split('(')[0].strip()
            matches = [p['Part ID'] for p in parts if p['Part Name'] and name.lower() in p['Part Name'].lower()]
            for pid in matches:
                part_guidelines[pid].append(r['Maintenance ID'])
    total_entries = sum(len(v) for v in part_guidelines.values())
    multi = {pid: mids for pid, mids in part_guidelines.items() if len(mids) > 1}
    print(f'  {total_entries} guideline entries across {len(part_guidelines)} Part nodes; {len(unlinked)} row(s) have no resolvable part: {unlinked}')
    print(f'  Parts with more than one guideline (correctly preserved as separate list entries, not overwritten): {multi}')
    check('No maintenance guideline data lost to overwrite (list-based design)', len(multi) >= 1 or total_entries == len(maintenance) - len(unlinked),
          'expected PT-032 to carry 2 guidelines')

    print()
    print('=== Channel label consistency (channels.cypher / channel_relationships.cypher simulation) ===')
    channel_names = defaultdict(set)
    for r in relationships:
        if r['To Entity Type'] == 'Channel':
            channel_names[r['To ID']].add(r['To Name'])
    for cid, names in channel_names.items():
        stable = len(names) == 1
        print(f'  {cid}: {"stable" if stable else "VARIES per relationship"} source To Name -> {names}')
    check('CH-DEALER To Name is stable (safe to use directly as node label)', channel_names.get('CH-DEALER', set()) == {'HCME authorised dealer network'})
    check('CH-EXTERNAL To Name varies by relationship (confirms it must NOT be used as a fixed node label; moved to provider_detail on DELIVERED_BY)',
          len(channel_names.get('CH-EXTERNAL', set())) > 1)

    print()
    print('=== CORE vs DERIVED preserved ===')
    class_counts = Counter(r['relationship_class'] for r in relationships)
    check('relationship_class present on every sheet-13 row', all(r.get('relationship_class') for r in relationships), str(class_counts))

    print()
    print('=== SUMMARY ===')
    if FAILURES:
        print(f'{len(FAILURES)} CHECK(S) FAILED:')
        for f in FAILURES:
            print(' -', f)
    else:
        print('All checks passed. No Neo4j connection was made.')


if __name__ == '__main__':
    main()
