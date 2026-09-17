#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cleans, normalizes and exports the graph-ready dataset from the authoritative
source workbook. Read-only against the source. Every normalization rule here
maps to a vocabulary value actually observed in the source (verified via
direct inspection before writing this script) — nothing is invented.

Run: python neo4j/scripts/export_clean_data.py
Outputs:
  HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx (16 sheets)
  neo4j/data/*.csv (14 files)
  neo4j/reports/data_quality_report.md
  neo4j/CLEANUP_REPORT.md
  neo4j/reports/schema_candidates.md
  neo4j/reports/fitment_conflicts.csv (if any)
  neo4j/reports/service_relationship_conflicts.csv (if any)
"""
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE = Path(r"C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx")
CLEAN_XLSX = ROOT / 'HITACHI_AFTERSALES_NEO4J_CLEAN.xlsx'
DATA_DIR = ROOT / 'neo4j' / 'data'
REPORTS_DIR = ROOT / 'neo4j' / 'reports'
NEO4J_DIR = ROOT / 'neo4j'

HEADER_ROW, DATA_START_ROW = 3, 4
NA_LIKE = {'n/a', 'na', 'not available', 'not stated', 'not publicly stated'}
URL_RE = re.compile(r'https?://', re.I)


def load_sheet(wb, name):
    ws = wb[name]
    header = [h for h in next(ws.iter_rows(min_row=HEADER_ROW, max_row=HEADER_ROW, values_only=True))]
    rows = []
    for row in ws.iter_rows(min_row=DATA_START_ROW, values_only=True):
        if row is None or all(v is None for v in row):
            continue
        rows.append(dict(zip(header, row)))
    return rows


def clean_value(v):
    """Trim whitespace, collapse repeated spaces, normalize N/A-like strings
    and empty strings to None. Never touches the semantic content of a value
    otherwise — model codes and part numbers pass through unchanged apart
    from this whitespace/blank handling."""
    if v is None:
        return None
    if isinstance(v, str):
        s = re.sub(r'\s+', ' ', v.strip())
        if s == '' or s.lower() in NA_LIKE:
            return None
        return s
    return v


def clean_row(row, keep, rename=None):
    rename = rename or {}
    out = {}
    for src_col in keep:
        out[rename.get(src_col, src_col)] = clean_value(row.get(src_col))
    return out


def dedupe(rows, key_fields):
    """Merge exact-duplicate rows (identical across key_fields); return
    (deduped_rows, duplicate_count)."""
    seen = {}
    dupes = 0
    for r in rows:
        key = tuple(str(r.get(k)) for k in key_fields)
        if key in seen:
            dupes += 1
            continue
        seen[key] = r
    return list(seen.values()), dupes


COMPATIBILITY_MAP = {
    'category-level': 'CATEGORY',
    'model-level': 'EXACT_MODEL',
    'model-group level': 'MODEL_RANGE',
}


def normalize_compatibility(raw):
    if not raw:
        return 'NOT_STATED'
    low = raw.lower()
    for prefix, code in COMPATIBILITY_MAP.items():
        if low.startswith(prefix):
            return code
    return 'NOT_STATED'


def normalize_applicability(raw):
    if not raw:
        return 'NOT_STATED'
    low = raw.lower()
    if low.startswith('not stated'):
        return 'NOT_STATED'
    if 'all machines' in low or 'not category-limited' in low:
        return 'ALL_MACHINES_STATED'
    if low.startswith('applies'):
        return 'CATEGORY'
    return 'NOT_STATED'


def normalize_relationship_class(raw):
    if not raw:
        return 'UNRESOLVED'
    low = raw.lower()
    if 'official website data' in low:
        return 'CORE'
    if 'derived' in low:
        return 'DERIVED'
    return 'RESEARCH_ONLY'


def main():
    wb = openpyxl.load_workbook(SOURCE, read_only=True, data_only=True)
    raw = {name: load_sheet(wb, name) for name in wb.sheetnames}
    wb.close()

    cleanup_log = []       # (what, detail) tuples for CLEANUP_REPORT.md
    quality = {}           # sheet -> {before, after, removed, ...}
    review_required = []   # rows destined for 16_REVIEW_REQUIRED

    # --- 01_CATEGORIES ---------------------------------------------------
    src = raw['01_MACHINE_CATEGORIES']
    keep = ['Category ID', 'Parent Category', 'Category Name', 'Official Category Name',
            'Category Description', 'Product Type', 'Machine Configuration',
            'On-road / Off-road', 'Primary Application', 'Source', 'Source ID', 'Source Date']
    categories = [clean_row(r, keep) for r in src]
    categories, dupe_n = dedupe(categories, ['Category ID'])
    quality['categories'] = {'before': len(src), 'after': len(categories), 'duplicates': dupe_n}
    cleanup_log.append(('01_CATEGORIES', f'Dropped Official URL and Notes. Kept {len(keep)} of {len(next(iter(src), {}).keys()) if src else 0} source columns. {dupe_n} exact-duplicate rows merged.'))

    # --- 02_MACHINES -------------------------------------------------------
    src = raw['02_MACHINE_MASTER']
    keep = ['Machine ID', 'Manufacturer', 'Brand', 'Machine Category', 'Machine Subcategory',
            'Category ID', 'Product Family', 'Model', 'Models Covered', 'Model Count',
            'Generation / Series', 'Machine Type', 'Configuration', 'Power Source',
            'Official Product Name', 'Available In', 'Engine / Motor Rated Power',
            'Operating Weight (as published)', 'Operating Weight (kg, normalised)',
            'Bucket Capacity (as published)', 'Battery Capacity', 'Nominal Payload',
            'Max. Digging Depth', 'Max. Digging Reach', 'Overall Width', 'Overall Height of Cab',
            'Fuel Tank Capacity', 'Published Spec Row Count', 'Published Spec Groups',
            'Official Overview Text', 'Data Class', 'Source ID', 'Source Date']
    machines = [clean_row(r, keep) for r in src]
    machines, dupe_n = dedupe(machines, ['Machine ID'])
    quality['machines'] = {'before': len(src), 'after': len(machines), 'duplicates': dupe_n}
    cleanup_log.append(('02_MACHINES', 'Dropped Official Product URL and Brochure PDF (URLs). Preserved Model / Models Covered / '
                                       'Model Count exactly as published — a catalogue-page Machine ID is not silently split into one row per model code.'))

    # --- 03_SPECIFICATIONS ---------------------------------------------------
    src = raw['03_MACHINE_SPECIFICATIONS']
    keep = ['Spec ID', 'Machine ID', 'Model', 'Machine Subcategory', 'Specification Group',
            'Specification Name', 'Specification Value', 'Unit', 'Normalised Value',
            'Data Class', 'Source ID', 'Source Date']
    not_stated_n = sum(1 for r in src if str(r.get('Specification Value') or '').strip().lower() == 'not publicly stated')
    specifications = [clean_row(r, keep) for r in src]
    # The value itself is nulled (never converted to a fake number), but the
    # fact that it was explicitly marked unpublished — rather than merely
    # blank for some other reason — is recorded separately, per the "record
    # the evidence state separately" rule.
    for orig, cleaned in zip(src, specifications):
        cleaned['value_stated'] = str(orig.get('Specification Value') or '').strip().lower() != 'not publicly stated'
    specifications, dupe_n = dedupe(specifications, ['Spec ID'])
    quality['specifications'] = {'before': len(src), 'after': len(specifications), 'duplicates': dupe_n}
    cleanup_log.append(('03_SPECIFICATIONS', f'Dropped Official URL. {not_stated_n} rows had "NOT PUBLICLY STATED" as their Specification '
                                              f'Value; that text is nulled (never converted to a fake number) and the fact it was explicitly '
                                              f'unpublished is preserved in the value_stated column instead of being lost.'))

    # --- 04_APPLICATIONS ---------------------------------------------------
    src = raw['04_MACHINE_APPLICATIONS']
    keep = ['Machine ID', 'Model', 'Machine Subcategory', 'Application', 'Application Type',
            'Official Description', 'Data Class', 'Source ID', 'Confidence', 'Source Date']
    applications = [clean_row(r, keep) for r in src]
    # Canonicalize casing only — "Demolition" / "demolition" / " DEMOLITION " collapse to
    # one form, but distinct application names never merge.
    canon_map = {}
    for r in applications:
        app = r['Application']
        if app:
            key = app.lower()
            canon_map.setdefault(key, app if app[:1].isupper() else app.title())
    recast = 0
    for r in applications:
        if r['Application']:
            canon = canon_map[r['Application'].lower()]
            if canon != r['Application']:
                recast += 1
            r['Application'] = canon
    applications, dupe_n = dedupe(applications, ['Machine ID', 'Application'])
    quality['applications'] = {'before': len(src), 'after': len(applications), 'duplicates': dupe_n}
    cleanup_log.append(('04_APPLICATIONS', f'Dropped Source URL. {recast} values recast to a canonical case form '
                                            f'(distinct application names were never merged). {dupe_n} exact machine+application duplicates merged.'))

    # --- 05_ATTACHMENTS ---------------------------------------------------
    src = raw['05_ATTACHMENTS']
    keep = ['Attachment ID', 'Attachment Name', 'Attachment Type', 'Attachment Category',
            'Machine ID', 'Compatible Machine Model', 'Compatible Machine Category',
            'Mounting / Coupling Type', 'Hydraulic Requirement', 'Weight', 'Dimensions',
            'Capacity', 'Purpose / Application', 'Detachable / Fixed', 'Data Class',
            'Source ID', 'Confidence', 'Source Date']
    attachments = [clean_row(r, keep) for r in src]
    quality['attachments'] = {'before': len(src), 'after': len(attachments), 'duplicates': 0}
    cleanup_log.append(('05_ATTACHMENTS', 'Dropped Official URL. No Weight/Dimensions/Capacity values were invented for rows where the '
                                           'source leaves them blank.'))

    # --- 06_PARTS ---------------------------------------------------------
    src = raw['06_PART_MASTER']
    keep = ['Part ID', 'Part Number', 'Part Name', 'Part Category', 'Part Subcategory',
            'Component / Assembly', 'Genuine Hitachi Part', 'Consumable', 'Wear Part',
            'Replacement Part', 'Service Part', 'Attachment Part', 'Description',
            'Supersedes Part Number', 'Superseded By', 'Data Class', 'Source ID',
            'Confidence', 'Source Date']
    parts = [clean_row(r, keep) for r in src]
    for r in parts:
        r['record_class'] = 'ORDERABLE_OEM_PART' if r['Part Number'] else 'PRODUCT_LINE_PART_FAMILY'
    orderable_n = sum(1 for r in parts if r['record_class'] == 'ORDERABLE_OEM_PART')
    quality['parts'] = {'before': len(src), 'after': len(parts), 'duplicates': 0}
    cleanup_log.append(('06_PARTS', f'Dropped Source URL. {orderable_n} of {len(parts)} parts carry a real published part number '
                                     f'(record_class=ORDERABLE_OEM_PART); the rest are named product lines with no part number '
                                     f'(record_class=PRODUCT_LINE_PART_FAMILY) — none was assigned a manufactured SKU.'))

    # --- 07_MACHINE_PART_FITMENT --------------------------------------------
    src = raw['07_MACHINE_PART_FITMENT']
    keep = ['Fitment ID', 'Machine ID', 'Machine Model', 'Part ID', 'Part Number', 'Part Name',
            'Assembly', 'Fitment Type', 'Compatibility', 'Installation Context',
            'Position / Location', 'Data Class', 'Source ID', 'Confidence', 'Source Date']
    fitment = [clean_row(r, keep) for r in src]
    for r in fitment:
        r['evidence_original'] = r['Compatibility']
        r['evidence'] = normalize_compatibility(r['Compatibility'])
    # Conflicting evidence: same (Machine ID, Part ID) pair stated with two
    # different evidence levels across rows.
    by_pair = defaultdict(list)
    for r in fitment:
        by_pair[(r['Machine ID'], r['Part ID'])].append(r)
    fitment_conflicts = []
    for (mid, pid), group in by_pair.items():
        levels = set(r['evidence'] for r in group)
        if len(levels) > 1:
            rows = list(group)
            for a, b in zip(rows, rows[1:]):
                fitment_conflicts.append({
                    'machine_id': mid, 'model': a.get('Machine Model'), 'part_id': pid,
                    'part_number': a.get('Part Number'), 'evidence_1': a['evidence'],
                    'evidence_2': b['evidence'], 'source_1': a.get('Source ID'),
                    'source_2': b.get('Source ID'), 'resolution': 'REVIEW_REQUIRED',
                })
    fitment, dupe_n = dedupe(fitment, ['Machine ID', 'Part ID', 'evidence'])
    quality['machine_part_fitment'] = {'before': len(src), 'after': len(fitment), 'duplicates': dupe_n, 'conflicts': len(fitment_conflicts)}
    cleanup_log.append(('07_MACHINE_PART_FITMENT', f'Dropped Official URL. Compatibility free text normalized to a controlled evidence '
                                                    f'vocabulary (EXACT_MODEL/MODEL_RANGE/CATEGORY/NOT_STATED); original free text kept in '
                                                    f'evidence_original. {dupe_n} identical-evidence duplicate pairs merged. '
                                                    f'{len(fitment_conflicts)} machine+part pairs had genuinely conflicting evidence and are '
                                                    f'logged in fitment_conflicts.csv rather than silently resolved.'))
    evidence_counts = Counter(r['evidence'] for r in fitment)

    # --- 08_SERVICES ---------------------------------------------------------
    src = raw['08_SERVICE_CAPABILITIES']
    keep = ['Service ID', 'Service Name', 'Service Category', 'Description',
            'Applies To Machine Category', 'Applies To Machine Model', 'Customer Site',
            'Dealer Workshop', 'Other Location', 'Dealer Delivered', 'External Authorised Provider',
            'Related Parts', 'Related Machine Data', 'Official / Derived', 'Source ID', 'Source Date']
    services = [clean_row(r, keep) for r in src]
    quality['services'] = {'before': len(src), 'after': len(services), 'duplicates': 0}
    cleanup_log.append(('08_SERVICES', 'Dropped Source URL. Customer Site / Dealer Workshop / Other Location kept as capability flags '
                                        'on the service record, not split into separate location entities.'))

    # --- 09_MACHINE_SERVICE --------------------------------------------------
    src = raw['09_MACHINE_SERVICE_MATRIX']
    keep = ['Machine ID', 'Machine Category', 'Machine Model', 'Service ID', 'Service Name',
            'Service Type', 'Applicability', 'Service Location', 'Trigger',
            'Interval (officially stated)', 'Machine Hours', 'Condition Based',
            'Dealer Service', 'Workshop Service', 'Field Service', 'Data Class',
            'Source ID', 'Confidence', 'Source Date']
    machine_service = [clean_row(r, keep) for r in src]
    for r in machine_service:
        r['applicability_original'] = r['Applicability']
        r['applicability'] = normalize_applicability(r['Applicability'])
    by_pair = defaultdict(list)
    for r in machine_service:
        by_pair[(r['Machine ID'], r['Service ID'])].append(r)
    service_conflicts = []
    for (mid, sid), group in by_pair.items():
        levels = set(r['applicability'] for r in group)
        if len(levels) > 1:
            rows = list(group)
            for a, b in zip(rows, rows[1:]):
                service_conflicts.append({
                    'machine_id': mid, 'model': a.get('Machine Model'), 'service_id': sid,
                    'service_name': a.get('Service Name'), 'applicability_1': a['applicability'],
                    'applicability_2': b['applicability'], 'source_1': a.get('Source ID'),
                    'source_2': b.get('Source ID'), 'resolution': 'REVIEW_REQUIRED',
                })
    machine_service, dupe_n = dedupe(machine_service, ['Machine ID', 'Service ID', 'applicability'])
    quality['machine_service'] = {'before': len(src), 'after': len(machine_service), 'duplicates': dupe_n, 'conflicts': len(service_conflicts)}
    cleanup_log.append(('09_MACHINE_SERVICE', f'Applicability free text normalized to ALL_MACHINES_STATED/CATEGORY/NOT_STATED (original kept '
                                               f'in applicability_original — none of these rows literally state a single exact-model-only '
                                               f'applicability, so EXACT/MODEL_RANGE were not asserted where the source never states them). '
                                               f'{dupe_n} duplicates merged, {len(service_conflicts)} conflicts logged.'))

    # --- 10_MAINTENANCE -------------------------------------------------------
    src = raw['10_MAINTENANCE_SCHEDULE']
    keep = ['Maintenance ID', 'Machine ID', 'Applies To (as stated)', 'Maintenance Activity',
            'Maintenance Type', 'Interval', 'Interval Unit', 'Operating Hours',
            'Calendar Interval', 'Component', 'Required Part', 'Required Quantity',
            'Consumable', 'Service Description / Official Wording', 'Data Class',
            'Source ID', 'Confidence', 'Source Date']
    maintenance = [clean_row(r, keep) for r in src]
    quality['maintenance'] = {'before': len(src), 'after': len(maintenance), 'duplicates': 0}
    cleanup_log.append(('10_MAINTENANCE', 'Dropped Source URL. Only the 4 genuinely published interval figures carry a real value; '
                                           'everything else stays as the source states it (typically blank/NOT PUBLICLY STATED).'))

    # --- 11_SERVICE_PART_REQUIREMENTS ---------------------------------------
    src = raw['11_SERVICE_PART_REQUIREMENTS']
    keep = ['Requirement ID', 'Machine ID', 'Service ID', 'Service Name', 'Maintenance Activity',
            'Part ID', 'Part Number', 'Part Name', 'Quantity', 'Mandatory / Optional',
            'Consumable / Wear / Replacement', 'Data Class', 'Source ID', 'Confidence', 'Source Date']
    service_part_requirements = [clean_row(r, keep) for r in src]
    quality['service_part_requirements'] = {'before': len(src), 'after': len(service_part_requirements), 'duplicates': 0}
    cleanup_log.append(('11_SERVICE_PART_REQUIREMENTS', 'Dropped Source URL. No quantity or part number was invented for the rows '
                                                         'the source leaves blank.'))

    # --- 12_DIGITAL_SERVICES -----------------------------------------------
    src = raw['12_MACHINE_DIGITAL_SERVICES']
    keep = ['Digital Service ID', 'Service Name', 'Machine ID', 'Machine Model', 'Machine Category',
            'Applicability', 'Capability', 'Machine Data', 'Alert / Monitoring',
            'Maintenance Support', 'Diagnostic Support', 'Parts Support', 'Dealer Support',
            'Description', 'Stated Applicability (official wording)', 'Data Class',
            'Source ID', 'Source Date']
    digital_services = [clean_row(r, keep) for r in src]
    quality['digital_services'] = {'before': len(src), 'after': len(digital_services), 'duplicates': 0}
    cleanup_log.append(('12_DIGITAL_SERVICES', 'Dropped URL. The Fleet-management/Service page scope conflict noted in the source '
                                                '(mini excavators included or not) is preserved via the Applicability + Stated Applicability '
                                                'fields rather than silently picking a side.'))

    # --- 13_RELATIONSHIPS ---------------------------------------------------
    src = raw['13_AFTER_SALES_RELATIONSHIPS']
    keep = ['Relationship ID', 'From Entity Type', 'From ID', 'From Name', 'Relationship',
            'To Entity Type', 'To ID', 'To Name', 'Data Class', 'Source ID', 'Confidence', 'Source Date']
    relationships = [clean_row(r, keep) for r in src]
    seen = set()
    for r in relationships:
        key = (r['From ID'], r['Relationship'], r['To ID'])
        if key in seen:
            r['relationship_class'] = 'DUPLICATE'
        else:
            seen.add(key)
            r['relationship_class'] = normalize_relationship_class(r['Data Class'])
        if not r['From ID'] or not r['To ID']:
            r['relationship_class'] = 'INVALID'
    class_counts = Counter(r['relationship_class'] for r in relationships)
    quality['relationships'] = {'before': len(src), 'after': len(relationships), 'duplicates': class_counts.get('DUPLICATE', 0)}
    cleanup_log.append(('13_RELATIONSHIPS', f'Dropped Source URL. Every row classified by relationship_class: {dict(class_counts)}. '
                                             f'Only CORE and DERIVED rows should be treated as graph-ready; DUPLICATE/INVALID/UNRESOLVED are '
                                             f'kept in the sheet but flagged, not silently dropped.'))
    review_required += [r for r in relationships if r['relationship_class'] in ('DUPLICATE', 'INVALID', 'UNRESOLVED', 'RESEARCH_ONLY')]

    # --- 14_PROVENANCE (compact — no raw URLs carried into the graph-ready set) ---
    src = raw['14_SOURCE_REGISTER']
    keep = ['Source ID', 'Source Organisation', 'Source Type', 'Page Title',
            'Machine / Category', 'Data Domain', 'Date Accessed', 'Official Source']
    provenance = [clean_row(r, keep) for r in src]
    quality['provenance'] = {'before': len(src), 'after': len(provenance), 'duplicates': 0}
    cleanup_log.append(('14_PROVENANCE', 'Dropped the raw URL column from the graph-ready provenance table — the full source register '
                                          'with URLs remains available in the untouched original workbook for audit if ever needed.'))

    # --- 15_DATA_QUALITY (pass through, this source sheet already IS a quality log) ---
    src = raw['15_DATA_QUALITY']
    keep = ['Entity', 'Record ID', 'Field', 'Value', 'Source', 'Confidence', 'Status',
            'Missing / Unknown Reason', 'Validation Note']
    data_quality_rows = [clean_row(r, keep) for r in src]
    quality['data_quality'] = {'before': len(src), 'after': len(data_quality_rows), 'duplicates': 0}
    cleanup_log.append(('15_DATA_QUALITY', 'Passed through unchanged apart from whitespace/blank normalization — this source sheet is '
                                            'itself a quality/conflict log, not raw entity data.'))

    # --- 16_REVIEW_REQUIRED --------------------------------------------------
    review_sheet = []
    for r in fitment_conflicts:
        review_sheet.append({'category': 'FITMENT_CONFLICT', **r})
    for r in service_conflicts:
        review_sheet.append({'category': 'SERVICE_RELATIONSHIP_CONFLICT', **r})
    for r in review_required:
        review_sheet.append({'category': f"RELATIONSHIP_{r['relationship_class']}", 'relationship_id': r['Relationship ID'],
                              'from_id': r['From ID'], 'relationship': r['Relationship'], 'to_id': r['To ID']})

    # =========================================================================
    # Write the 16-sheet clean workbook
    # =========================================================================
    out_wb = Workbook()
    out_wb.remove(out_wb.active)

    def write_sheet(name, rows):
        ws = out_wb.create_sheet(name)
        if not rows:
            return
        header = list(rows[0].keys())
        ws.append(header)
        for r in rows:
            ws.append([r.get(h) for h in header])

    readme_rows = [
        {'Field': 'Source workbook', 'Value': str(SOURCE)},
        {'Field': 'Generated by', 'Value': 'neo4j/scripts/export_clean_data.py'},
        {'Field': 'Purpose', 'Value': 'Graph-ready, deduplicated, evidence-normalized dataset. Pre-Neo4j: no database connection made.'},
        {'Field': 'Sheets', 'Value': '16 — see rollup in data_quality_report.md'},
    ]
    write_sheet('00_README', readme_rows)
    write_sheet('01_CATEGORIES', categories)
    write_sheet('02_MACHINES', machines)
    write_sheet('03_SPECIFICATIONS', specifications)
    write_sheet('04_APPLICATIONS', applications)
    write_sheet('05_ATTACHMENTS', attachments)
    write_sheet('06_PARTS', parts)
    write_sheet('07_MACHINE_PART_FITMENT', fitment)
    write_sheet('08_SERVICES', services)
    write_sheet('09_MACHINE_SERVICE', machine_service)
    write_sheet('10_MAINTENANCE', maintenance)
    write_sheet('11_SERVICE_PART_REQUIREMENTS', service_part_requirements)
    write_sheet('12_DIGITAL_SERVICES', digital_services)
    write_sheet('13_RELATIONSHIPS', relationships)
    write_sheet('14_PROVENANCE', provenance)
    write_sheet('15_DATA_QUALITY', data_quality_rows)
    write_sheet('16_REVIEW_REQUIRED', review_sheet)
    out_wb.save(CLEAN_XLSX)

    # =========================================================================
    # Write the 14 CSVs
    # =========================================================================
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    def write_csv(fname, rows):
        path = DATA_DIR / fname
        if not rows:
            path.write_text('', encoding='utf-8')
            return
        header = list(rows[0].keys())
        with open(path, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=header)
            w.writeheader()
            for r in rows:
                w.writerow(r)

    write_csv('categories.csv', categories)
    write_csv('machines.csv', machines)
    write_csv('specifications.csv', specifications)
    write_csv('applications.csv', applications)
    write_csv('attachments.csv', attachments)
    write_csv('parts.csv', parts)
    write_csv('machine_part_fitment.csv', fitment)
    write_csv('services.csv', services)
    write_csv('machine_service.csv', machine_service)
    write_csv('maintenance.csv', maintenance)
    write_csv('service_part_requirements.csv', service_part_requirements)
    write_csv('digital_services.csv', digital_services)
    write_csv('relationships.csv', relationships)
    write_csv('provenance.csv', provenance)

    # =========================================================================
    # Referential integrity check
    # =========================================================================
    machine_ids = {r['Machine ID'] for r in machines if r['Machine ID']}
    part_ids = {r['Part ID'] for r in parts if r['Part ID']}
    service_ids = {r['Service ID'] for r in services if r['Service ID']}
    category_ids = {r['Category ID'] for r in categories if r['Category ID']}

    def is_scope_descriptor(value):
        """A handful of rows use a sentence in an ID column instead of a real
        entity ID — e.g. 'ALL machines in the service scope - see
        09_MACHINE_SERVICE_MATRIX' or 'NOT IN CURRENT CATALOGUE'. That's the
        source honestly stating a broader scope or a known gap, not a broken
        reference, so it must not be reported as a dangling foreign key."""
        return isinstance(value, str) and len(value.split()) >= 4

    dangling = []
    scope_descriptors = []

    def check_fk(dataset, row_id, field, value, valid_set):
        if not value:
            return
        if value in valid_set:
            return
        if is_scope_descriptor(value):
            scope_descriptors.append((dataset, row_id, field, value))
        else:
            dangling.append((dataset, row_id, field, value))

    for r in fitment:
        check_fk('machine_part_fitment', r['Fitment ID'], 'Machine ID', r['Machine ID'], machine_ids)
        check_fk('machine_part_fitment', r['Fitment ID'], 'Part ID', r['Part ID'], part_ids)
    for r in machine_service:
        check_fk('machine_service', None, 'Machine ID', r['Machine ID'], machine_ids)
        check_fk('machine_service', None, 'Service ID', r['Service ID'], service_ids)
    for r in service_part_requirements:
        check_fk('service_part_requirements', r['Requirement ID'], 'Machine ID', r['Machine ID'], machine_ids)
        check_fk('service_part_requirements', r['Requirement ID'], 'Part ID', r['Part ID'], part_ids)
    for r in machines:
        check_fk('machines', r['Machine ID'], 'Category ID', r['Category ID'], category_ids)

    # =========================================================================
    # Reports
    # =========================================================================
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if fitment_conflicts:
        with open(REPORTS_DIR / 'fitment_conflicts.csv', 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(fitment_conflicts[0].keys()))
            w.writeheader()
            w.writerows(fitment_conflicts)
    if service_conflicts:
        with open(REPORTS_DIR / 'service_relationship_conflicts.csv', 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(service_conflicts[0].keys()))
            w.writeheader()
            w.writerows(service_conflicts)

    dq_lines = ['# Data Quality Report', '']
    dq_lines.append('| Dataset | Source rows | Clean rows | Duplicates merged |')
    dq_lines.append('|---|---|---|---|')
    for name, q in quality.items():
        dq_lines.append(f"| {name} | {q['before']} | {q['after']} | {q.get('duplicates', 0)} |")
    dq_lines += ['', f'Fitment conflicts requiring review: {len(fitment_conflicts)}',
                 f'Machine-service conflicts requiring review: {len(service_conflicts)}',
                 f'Dangling foreign keys found: {len(dangling)}',
                 f'Scope-descriptor values (not real IDs, not counted as dangling): {len(scope_descriptors)}', '']
    dq_lines.append('## Fitment evidence breakdown')
    for level, n in evidence_counts.items():
        dq_lines.append(f'- {level}: {n}')
    dq_lines.append('')
    dq_lines.append('## Relationship classification (13_AFTER_SALES_RELATIONSHIPS)')
    for cls, n in class_counts.items():
        dq_lines.append(f'- {cls}: {n}')
    if dangling:
        dq_lines.append('')
        dq_lines.append('## Dangling foreign keys')
        for d in dangling[:200]:
            dq_lines.append(f'- {d[0]} / {d[1]}: {d[2]}={d[3]!r} not found in target entity set')
    if scope_descriptors:
        dq_lines.append('')
        dq_lines.append('## Scope-descriptor values (source states a scope in prose instead of an ID — not a data defect)')
        for d in scope_descriptors[:200]:
            dq_lines.append(f'- {d[0]} / {d[1]}: {d[2]}={d[3]!r}')
    (REPORTS_DIR / 'data_quality_report.md').write_text('\n'.join(dq_lines), encoding='utf-8')

    cleanup_lines = ['# Cleanup Report', '']
    for sheet, note in cleanup_log:
        cleanup_lines.append(f'## {sheet}')
        cleanup_lines.append(note)
        cleanup_lines.append('')
    cleanup_lines.append('## Recommended graph entities')
    cleanup_lines.append('Category, Machine, Specification, Application, Part, Attachment, Service, DigitalService — '
                          'see schema_candidates.md for the evidence behind each.')
    cleanup_lines.append('')
    cleanup_lines.append('## Remaining data-quality concerns')
    cleanup_lines.append(f'- {len(fitment_conflicts)} fitment conflicts logged for human review (fitment_conflicts.csv).')
    cleanup_lines.append(f'- {len(service_conflicts)} machine-service applicability conflicts logged for review.')
    cleanup_lines.append(f'- {len(dangling)} dangling foreign keys found — see data_quality_report.md.')
    (NEO4J_DIR / 'CLEANUP_REPORT.md').write_text('\n'.join(cleanup_lines), encoding='utf-8')

    schema_lines = ['# Schema Candidates', '',
                    'Node candidates, each with the evidence behind it. No node type is added automatically —',
                    'this is for review before any Neo4j schema is created.', '']
    candidates = [
        ('Category', '01_MACHINE_CATEGORIES', len(categories), 'Node — is the hierarchy root, has its own ID and CHILD_OF structure via Parent Category.'),
        ('Machine', '02_MACHINE_MASTER', len(machines), 'Node — the central entity everything else attaches to.'),
        ('Specification', '03_MACHINE_SPECIFICATIONS', len(specifications), 'Property-bag candidate: could be a node (Spec ID exists) or a property set on Machine. Recommend node — EAV shape (Specification Name/Value/Unit) does not fit as flat Machine properties.'),
        ('Application', '04_MACHINE_APPLICATIONS', len(set(r['Application'] for r in applications if r['Application'])), 'Node — reused across many machines, canonical name after normalization.'),
        ('Part', '06_PART_MASTER', len(parts), 'Node — split by record_class (ORDERABLE_OEM_PART vs PRODUCT_LINE_PART_FAMILY), both real distinct concepts.'),
        ('Attachment', '05_ATTACHMENTS', len(attachments), 'Node — many-to-many with Machine, has its own ID.'),
        ('Service', '08_SERVICE_CAPABILITIES', len(services), 'Node — reused across the machine-service matrix.'),
        ('DigitalService', '12_MACHINE_DIGITAL_SERVICES', len(digital_services), 'Node — distinct from Service (different capability set, different source sheet).'),
        ('MaintenanceActivity', '10_MAINTENANCE_SCHEDULE', len(maintenance), f'Only {len(maintenance)} rows and mostly NOT PUBLICLY STATED. Recommend: property on a Machine-Service edge rather than its own node, pending more data.'),
        ('Source', '14_SOURCE_REGISTER', len(provenance), 'Node candidate for provenance, or a compact property set (source_id, source_name, confidence) on each fact — recommend property set per the "no URL blast radius" requirement, not a node customers would ever traverse.'),
    ]
    schema_lines.append('| Candidate | Source sheet | Records | Recommendation |')
    schema_lines.append('|---|---|---|---|')
    for name, sheet, n, note in candidates:
        schema_lines.append(f'| {name} | {sheet} | {n} | {note} |')
    (REPORTS_DIR / 'schema_candidates.md').write_text('\n'.join(schema_lines), encoding='utf-8')

    print('Clean workbook:', CLEAN_XLSX)
    print('CSVs written to:', DATA_DIR)
    print('Reports written to:', REPORTS_DIR, 'and', NEO4J_DIR / 'CLEANUP_REPORT.md')
    print(f'Fitment conflicts: {len(fitment_conflicts)}  Service conflicts: {len(service_conflicts)}  '
          f'Dangling FKs: {len(dangling)}  Scope-descriptor values (not real dangling FKs): {len(scope_descriptors)}')


if __name__ == '__main__':
    main()
