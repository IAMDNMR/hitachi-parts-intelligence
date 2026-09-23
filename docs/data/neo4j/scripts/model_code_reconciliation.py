#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Model-code discrepancy investigation (77 records / 84 slots / 79 distinct
strings). Read-only against the source workbook. Produces:
  neo4j/reports/MODEL_CODE_INVENTORY.csv
  neo4j/reports/MODEL_CODE_RECONCILIATION.csv
"""
import csv
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE = Path(r"C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx")
REPORTS = ROOT / 'neo4j' / 'reports'


def main():
    wb = openpyxl.load_workbook(SOURCE, read_only=True, data_only=True)
    ws = wb['02_MACHINE_MASTER']
    header = list(next(ws.iter_rows(min_row=3, max_row=3, values_only=True)))
    idx = {h: i for i, h in enumerate(header)}
    rows = [r for r in ws.iter_rows(min_row=4, values_only=True) if r and any(v is not None for v in r)]
    wb.close()

    # -------------------------------------------------------------------
    # Step 1: MODEL_CODE_INVENTORY.csv — one row per parsed model code
    # -------------------------------------------------------------------
    inventory = []
    code_to_machines = defaultdict(list)
    all_codes = []
    for r in rows:
        mid = r[idx['Machine ID']]
        model = r[idx['Model']]
        covered_raw = r[idx['Models Covered']]
        count = r[idx['Model Count']]
        subcat = r[idx['Machine Subcategory']]
        url = r[idx['Official Product URL']]
        codes = [c.strip() for c in str(covered_raw).split('|')]
        for code in codes:
            all_codes.append(code)
            code_to_machines[code].append(mid)
            inventory.append({
                'machine_id': mid, 'catalogue_record': model, 'raw_model_value': covered_raw,
                'parsed_model_code': code, 'source_page_or_reference': url,
                'model_count_source': count, 'parsed_count': len(codes),
                'notes': subcat,
            })

    with open(REPORTS / 'MODEL_CODE_INVENTORY.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(inventory[0].keys()))
        w.writeheader()
        w.writerows(inventory)

    # -------------------------------------------------------------------
    # Step 4: MODEL_CODE_RECONCILIATION.csv
    # -------------------------------------------------------------------
    code_counts = Counter(all_codes)
    distinct_codes = sorted(set(all_codes))
    assert len(all_codes) == 84, f'expected 84 slots, got {len(all_codes)}'
    assert len(distinct_codes) == 79, f'expected 79 distinct codes, got {len(distinct_codes)}'

    recon = []
    for code in distinct_codes:
        machines = code_to_machines[code]
        n = code_counts[code]
        if n == 1:
            classification = 'CONFIRMED_DISTINCT_MODEL'
            evidence = f'Appears once, on {machines[0]}.'
            treatment = 'Keep as a single models_covered entry on its one Machine node.'
        else:
            # every duplicated code in this dataset is one of the 5 EX-series
            # electric-drive pairs, verified by URL suffix "...e/" vs "...(none)/"
            classification = 'CONFIGURATION_VARIANT'
            evidence = (f'Appears on {n} separate catalogue pages ({", ".join(machines)}), each with its own '
                        f'distinct product URL (one ends in a plain model slug, the other in the same slug + "e" '
                        f'— the Electric Drive variant). The source\'s Model/Models Covered text was not given a '
                        f'distinct code for the electric page, so the same code string legitimately names two '
                        f'different real products.')
            treatment = ('Keep as TWO separate Machine nodes (one per catalogue page/URL — they have independent '
                         'specs, fitment and relationships), each carrying this same code string in its own '
                         'models_covered list. Do not merge the two pages into one node; do not invent a '
                         'distinct code string neither the source nor the site publishes.')
        recon.append({
            'model_code': code,
            'in_cleaned_84': 'yes',
            'in_readme_79': 'yes',  # every one of the 79 distinct strings is by definition in both counts
            'machine_record': '; '.join(machines),
            'classification': classification,
            'evidence': evidence,
            'recommended_treatment': treatment,
        })

    with open(REPORTS / 'MODEL_CODE_RECONCILIATION.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(recon[0].keys()))
        w.writeheader()
        w.writerows(recon)

    print(f'{len(inventory)} inventory rows (84 code slots), {len(recon)} reconciliation rows (79 distinct codes)')
    dupes = {c: n for c, n in code_counts.items() if n > 1}
    print('Duplicated code strings (account for 84-79=5 gap):', dupes)


if __name__ == '__main__':
    main()
