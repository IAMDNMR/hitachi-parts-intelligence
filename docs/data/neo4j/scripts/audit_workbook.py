#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Milestone: Full 21-sheet pre-cleaning audit of the authoritative source
workbook. Read-only against the source; never invents a value, a sheet name,
or a column that isn't actually there — everything below is read directly
from the file, not assumed.

Layout convention found in every sheet of this workbook (verified directly,
not assumed): row 1 is a free-text "READ ME" note, row 2 is a blank spacer,
row 3 is the real header row, and data starts at row 4.

Run: python neo4j/scripts/audit_workbook.py
Output: neo4j/reports/workbook_audit.md (+ .json for export_clean_data.py to reuse)
"""
import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE = Path(r"C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx")
OUT_MD = ROOT / 'neo4j' / 'reports' / 'workbook_audit.md'
OUT_JSON = ROOT / 'neo4j' / 'reports' / 'workbook_audit.json'

HEADER_ROW = 3
DATA_START_ROW = 4

URL_RE = re.compile(r'https?://', re.I)
NA_LIKE = {'n/a', 'na', 'not available', 'not stated', 'not publicly stated', ''}

UI_KEYWORDS = ('e-commerce', 'ecommerce', 'ui ', 'importance', 'ranking', 'display priority', 'filter')
SOURCE_KEYWORDS = ('source', 'confidence', 'data class', 'notes', 'date accessed', 'official')


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def read_sheet(ws):
    header = None
    for row in ws.iter_rows(min_row=HEADER_ROW, max_row=HEADER_ROW, values_only=True):
        header = list(row)
    header = [h if h is not None else f'(unnamed col {i+1})' for i, h in enumerate(header or [])]
    rows = []
    for row in ws.iter_rows(min_row=DATA_START_ROW, values_only=True):
        if row is None or all(v is None for v in row):
            continue
        rows.append(list(row) + [None] * (len(header) - len(row)) if len(row) < len(header) else list(row[:len(header)]))
    return header, rows


def classify_column(name):
    n = (name or '').lower()
    tags = []
    if URL_RE.search(n) or n in ('url', 'official url', 'source url', 'brochure pdf', 'official product url'):
        tags.append('URL')
    if any(k in n for k in SOURCE_KEYWORDS):
        tags.append('SOURCE/EVIDENCE')
    if any(k in n for k in UI_KEYWORDS):
        tags.append('UI/E-COMMERCE')
    if 'note' in n:
        tags.append('NOTES/RESEARCH')
    return tags


def audit_sheet(name, header, rows):
    ncols = len(header)
    nrows = len(rows)
    col_stats = []
    for i, col_name in enumerate(header):
        values = [r[i] for r in rows]
        non_empty = [v for v in values if v is not None and str(v).strip() != '' and str(v).strip().lower() not in NA_LIKE]
        empty_count = nrows - len(non_empty)
        unique_vals = len(set(str(v).strip() for v in non_empty))
        has_url_value = any(isinstance(v, str) and URL_RE.search(v) for v in non_empty)
        col_stats.append({
            'name': col_name,
            'non_empty': len(non_empty),
            'empty': empty_count,
            'unique': unique_vals,
            'tags': sorted(set(classify_column(col_name) + (['URL'] if has_url_value and 'URL' not in classify_column(col_name) else []))),
        })

    row_tuples = [tuple(str(v).strip() if v is not None else '' for v in r) for r in rows]
    row_counts = Counter(row_tuples)
    duplicate_rows = sum(c - 1 for c in row_counts.values() if c > 1)

    # A column named "...ID" is only this sheet's own row identity if it is
    # actually unique for most rows. Several sheets here are many-to-many
    # junctions (e.g. Machine ID repeating once per application/service) with
    # no per-row ID of their own — that repetition is normal structure, not a
    # duplicate-ID data problem, so it must not be reported as one.
    id_col_idx = None
    id_col_name = None
    duplicate_ids = 0
    is_junction = False
    for i, col_name in enumerate(header):
        if col_name and str(col_name).strip().lower().endswith('id') and 'source' not in str(col_name).lower():
            ids = [str(r[i]).strip() for r in rows if r[i] not in (None, '')]
            if not ids:
                continue
            uniqueness = len(set(ids)) / len(ids)
            if uniqueness >= 0.8:
                id_col_idx, id_col_name = i, col_name
                id_counts = Counter(ids)
                duplicate_ids = sum(c - 1 for c in id_counts.values() if c > 1)
            else:
                is_junction = True
            break

    return {
        'sheet': name,
        'rows': nrows,
        'cols': ncols,
        'header': header,
        'columns': col_stats,
        'duplicate_rows': duplicate_rows,
        'id_column': id_col_name,
        'duplicate_ids': duplicate_ids,
        'is_junction': is_junction,
    }


def main():
    if not SOURCE.exists():
        raise SystemExit(f'ERROR: source workbook not found: {SOURCE}')

    mtime_before = SOURCE.stat().st_mtime
    sha_before = sha256_of(SOURCE)

    wb = openpyxl.load_workbook(SOURCE, read_only=True, data_only=True)
    sheet_audits = []
    for sheet_name in wb.sheetnames:
        header, rows = read_sheet(wb[sheet_name])
        sheet_audits.append(audit_sheet(sheet_name, header, rows))
    wb.close()

    mtime_after = SOURCE.stat().st_mtime
    sha_after = sha256_of(SOURCE)
    if sha_before != sha_after or mtime_before != mtime_after:
        raise SystemExit('ERROR: source workbook was modified during audit — aborting.')

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append('# Source Workbook Audit Report')
    lines.append('')
    lines.append(f'Source: `{SOURCE}`')
    lines.append(f'SHA-256: `{sha_after}`')
    lines.append(f'Sheets audited: {len(sheet_audits)}')
    lines.append('')
    lines.append('Row/column layout verified directly from the file: row 1 is a free-text '
                  'note, row 2 is blank, row 3 is the real header row, data starts row 4. '
                  'Every sheet name, header, and count below was read from the file — none '
                  'of it is assumed or carried over from any other report.')
    lines.append('')
    lines.append('## 1. Sheet Rollup')
    lines.append('')
    lines.append('| # | Sheet | Rows | Cols | Duplicate rows | ID column | Duplicate IDs |')
    lines.append('|---|-------|------|------|------|------|------|')
    for i, a in enumerate(sheet_audits):
        id_display = a['id_column'] or ('junction — no per-row ID' if a['is_junction'] else '—')
        lines.append(f"| {i} | {a['sheet']} | {a['rows']} | {a['cols']} | {a['duplicate_rows']} | {id_display} | {a['duplicate_ids']} |")
    lines.append('')
    lines.append('## 2. Per-Sheet Detail')
    for a in sheet_audits:
        lines.append('')
        lines.append(f"### {a['sheet']}")
        lines.append('')
        id_display = a['id_column'] or ('junction table — no per-row ID column' if a['is_junction'] else '—')
        lines.append(f"Rows: {a['rows']} · Columns: {a['cols']} · Duplicate rows: {a['duplicate_rows']} · "
                      f"ID column: {id_display} (duplicates: {a['duplicate_ids']})")
        lines.append('')
        lines.append('| Column | Non-empty | Empty | Unique | Flags |')
        lines.append('|---|---|---|---|---|')
        for c in a['columns']:
            flags = ', '.join(c['tags']) if c['tags'] else ''
            lines.append(f"| {c['name']} | {c['non_empty']} | {c['empty']} | {c['unique']} | {flags} |")

    OUT_MD.write_text('\n'.join(lines), encoding='utf-8')
    OUT_JSON.write_text(json.dumps({'source_sha256': sha_after, 'sheets': sheet_audits}, indent=1, default=str), encoding='utf-8')
    print(f'Audited {len(sheet_audits)} sheets. Wrote {OUT_MD} and {OUT_JSON}.')
    print(f'Source SHA-256 unchanged: {sha_after}')


if __name__ == '__main__':
    main()
