# Milestone 1: Audit Report Format, CLI Interface & Validation Specification

**Agent**: `explorer_m1_3` (Audit Report Format & CLI Interface Explorer)  
**Milestone**: M1 (Discovery & Source Audit)  
**Working Directory**: `c:\Users\iamdn\OneDrive\Desktop\Parts&Service\.agents\explorer_m1_3`  
**Target Script**: `audit_workbook.py`  
**Target Report**: `neo4j/reports/workbook_audit.md`  
**Date**: 2026-09-17  
**Status**: COMPLETE — AUTHORITATIVE SPECIFICATION READY FOR WORKER IMPLEMENTATION  

---

## 1. Executive Summary & Problem Scope

This specification establishes the authoritative design for the pre-cleaning source audit instrument `audit_workbook.py` and its primary reporting deliverable `neo4j/reports/workbook_audit.md`.

In accordance with user requirement **R1** (`ORIGINAL_REQUEST.md`) and the project architecture (`PROJECT.md`), the audit tool must non-destructively inspect all **21 worksheets** in the authoritative source workbook:
`C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx` (~796 KB).

### 1.1 Core Mission Objectives
1. **Define Exact Markdown Template & Table Structures**: Design the complete schema for `neo4j/reports/workbook_audit.md` ensuring uniform metrics across all 21 source sheets: row/col dimensions, column catalog, fill rates, primary key uniqueness, duplicate detection, data hygiene flags (URLs, e-commerce noise, sentinel values), and graph utility classification.
2. **Define CLI Interface & Strict Exit Code Contract**: Specify the command-line argument parser, help text, option semantics, and the exact 4-tier exit code contract:
   - `0`: Success (all 21 sheets parsed, markdown written, hash match)
   - `1`: Bad arguments or syntax error
   - `2`: Missing source workbook or unreadable archive
   - `3`: Source modified / SHA-256 hash mismatch (immutability violation)
3. **Specify Worker & Reviewer Acceptance Suite**: Detail executable CLI verification commands, automated test assertions, and a reviewer sign-off checklist to guarantee 100% determinism, byte-for-byte reproducibility, and zero Neo4j network calls.

### 1.2 Non-Negotiable Architectural Constraints
- **Source Immutability**: The source workbook must remain 100% untouched. SHA-256 hash and OS timestamp (`st_mtime`) must be verified before and after execution.
- **Strict Neo4j Isolation Guardrail**: Under NO circumstances may `audit_workbook.py` connect to Neo4j, load database drivers, or access network sockets. The script operates 100% offline.
- **Byte-Level Determinism**: Successive runs on the same input workbook must generate bit-for-bit identical markdown reports. Dynamic timestamps (`datetime.now()`) are strictly banned from report output.

---

## 2. CLI Interface & Exit Code Contract Specification

### 2.1 Invocation Syntax

```bash
python audit_workbook.py [-h] [--input INPUT_PATH] [--output OUTPUT_PATH]
                         [--json-out JSON_PATH] [--verify-source] [--strict]
                         [--quiet] [--version]
```

### 2.2 CLI Argument Catalog

| Option | Short | Type | Default Value | Description & Behavior |
|---|---|---|---|---|
| `--input` | `-i` | `str` / `Path` | `C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx` | Path to the authoritative raw 21-sheet source Excel workbook. Must exist and be readable. |
| `--output` | `-o` | `str` / `Path` | `neo4j/reports/workbook_audit.md` | Destination path for the generated Markdown audit report. Parent directories are created automatically if missing. |
| `--json-out` | `-j` | `str` / `Path` | `None` | (Optional) Path to serialize raw structured audit metrics as JSON for programmatic test harness assertions. |
| `--verify-source` | | `bool` | `True` | Pre- and post-read SHA-256 hash verification. Aborts with exit code 3 if hash or modification time changes. |
| `--no-verify-source`| | `flag` | `False` | Disables post-read hash verification (primarily for test harness mocking; disabled by default). |
| `--strict` | `-s` | `flag` | `False` | Enables strict mode: fails with exit code 1 if sheet count < 21, unexpected headers, or malformed data tables are detected. |
| `--quiet` | `-q` | `flag` | `False` | Suppresses standard console stdout logging. Errors and critical diagnostics are still printed to stderr. |
| `--version` | `-v` | `flag` | N/A | Prints script version string (`audit_workbook.py 1.0.0`) and terminates immediately with exit code 0. |
| `--help` | `-h` | `flag` | N/A | Displays standardized help message, option descriptions, exit code definitions, and terminates with exit code 0. |

### 2.3 Formatted Help Message Output (`python audit_workbook.py --help`)

The CLI argument parser must produce the following verbatim help layout:

```text
usage: audit_workbook.py [-h] [-i INPUT] [-o OUTPUT] [-j JSON_OUT]
                         [--verify-source | --no-verify-source] [-s] [-q] [-v]

Hitachi OEM After-Sales Data Foundation — 21-Sheet Pre-Cleaning Source Auditor

options:
  -h, --help            show this help message and exit
  -i, --input INPUT     Path to source Excel workbook (default: C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx)
  -o, --output OUTPUT   Path to output Markdown audit report (default: neo4j/reports/workbook_audit.md)
  -j, --json-out JSON_OUT
                        Optional path to export raw audit metrics as JSON
  --verify-source       Enforce pre/post-read SHA-256 and timestamp check (default: True)
  --no-verify-source    Bypass post-read hash check (test mode only)
  -s, --strict          Fail on missing sheets, empty tables, or critical schema anomalies
  -q, --quiet           Suppress console stdout (errors written to stderr)
  -v, --version         show program's version number and exit

Exit Codes:
  0 = Success: All 21 sheets audited, report written, source immutability verified
  1 = Bad arguments or CLI syntax error
  2 = Missing source workbook or unreadable file / bad zip archive
  3 = Source file modified or SHA-256 hash mismatch (immutability violation)
```

### 2.4 Strict Exit Code Contract

The script must strictly govern process termination using standard `sys.exit(code)` semantics:

| Exit Code | Semantic Status | Triggering Conditions | Required Console Output (stderr) |
|:---:|---|---|---|
| **0** | **SUCCESS** | - All 21 sheets successfully opened and audited.<br>- Metrics computed without unhandled exceptions.<br>- Markdown report written to disk.<br>- Source SHA-256 hash and `st_mtime` identical before vs after. | If not `--quiet`, summary of audited sheets and output file location written to `stdout`. |
| **1** | **BAD ARGUMENTS** | - Unrecognized CLI arguments or flags (e.g. `--unknown-arg`).<br>- Missing required parameter arguments (e.g. `--input` without a path).<br>- Invalid flag combinations or value type parse errors.<br>- Validation failure under `--strict` mode (e.g. sheet count != 21). | `ERROR [ARG_PARSER]: <details>` written to `stderr`. Usage hint printed. |
| **2** | **MISSING SOURCE / UNREADABLE** | - Source file does not exist at `--input` path (`FileNotFoundError`).<br>- OS read permission denied (`PermissionError`).<br>- File is not a valid ZIP/OpenXML spreadsheet (`zipfile.BadZipFile`, `openpyxl.utils.exceptions.InvalidFileException`).<br>- Input file has 0 bytes. | `ERROR [SOURCE_UNREADABLE]: <file_path> could not be loaded. <reason>` written to `stderr`. |
| **3** | **SOURCE MODIFIED / HASH MISMATCH** | - Pre-read SHA-256 hash != post-read SHA-256 hash.<br>- Pre-read `os.stat().st_mtime` != post-read `st_mtime`.<br>- Attempt to open source workbook in write mode or save changes. | `CRITICAL [IMMUTABILITY_BREACH]: Source file modified during audit! Pre-hash: <h1>, Post-hash: <h2>` written to `stderr`. |

### 2.5 ArgumentParser Implementation Architecture

To ensure strict compliance with the exit code contract, the worker must customize `argparse.ArgumentParser` so that syntax errors reliably return exit code 1 rather than Python's default exit code 2:

```python
import argparse
import sys
from pathlib import Path

class AuditArgumentParser(argparse.ArgumentParser):
    """Custom parser ensuring argument parsing failures return exit code 1."""
    def error(self, message: str) -> None:
        sys.stderr.write(f"ERROR [BAD_ARGUMENTS]: {message}\n")
        sys.stderr.write("Run 'python audit_workbook.py --help' for usage instructions.\n")
        sys.exit(1)

def build_cli_parser() -> AuditArgumentParser:
    default_input = Path(r"C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx")
    default_output = Path("neo4j/reports/workbook_audit.md")
    
    parser = AuditArgumentParser(
        prog="audit_workbook.py",
        description="Hitachi OEM After-Sales Data Foundation — 21-Sheet Pre-Cleaning Source Auditor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exit Codes:
  0 = Success: All 21 sheets audited, report written, source immutability verified
  1 = Bad arguments or CLI syntax error
  2 = Missing source workbook or unreadable file / bad zip archive
  3 = Source file modified or SHA-256 hash mismatch (immutability violation)
"""
    )
    
    parser.add_argument(
        "-i", "--input",
        type=Path,
        default=default_input,
        help=f"Path to source Excel workbook (default: {default_input})"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=default_output,
        help=f"Path to output Markdown audit report (default: {default_output})"
    )
    parser.add_argument(
        "-j", "--json-out",
        type=Path,
        default=None,
        help="Optional path to export raw audit metrics as JSON"
    )
    parser.add_argument(
        "--verify-source",
        dest="verify_source",
        action="store_true",
        default=True,
        help="Enforce pre/post-read SHA-256 and timestamp check (default: True)"
    )
    parser.add_argument(
        "--no-verify-source",
        dest="verify_source",
        action="store_false",
        help="Bypass post-read hash check (test mode only)"
    )
    parser.add_argument(
        "-s", "--strict",
        action="store_true",
        help="Fail on missing sheets, empty tables, or critical schema anomalies"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress console stdout (errors written to stderr)"
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version="audit_workbook.py 1.0.0 (HCME Data Foundation Pipeline)"
    )
    return parser
```

### 2.6 Error Routing & Exit Dispatch Pattern

The top-level `main()` execution wrapper must handle errors and map exceptions to exit codes cleanly:

```python
def main() -> None:
    parser = build_cli_parser()
    args = parser.parse_args()
    
    # 1. Validate source path existence and readability (Exit code 2)
    if not args.input.exists() or not args.input.is_file():
        sys.stderr.write(f"ERROR [MISSING_SOURCE]: Source file not found at {args.input}\n")
        sys.exit(2)
        
    try:
        # 2. Execute audit pipeline
        audit_engine = WorkbookAuditor(
            input_path=args.input,
            output_path=args.output,
            json_path=args.json_out,
            verify_source=args.verify_source,
            strict=args.strict,
            quiet=args.quiet
        )
        audit_engine.run()
        sys.exit(0)
        
    except FileNotFoundError as e:
        sys.stderr.write(f"ERROR [MISSING_SOURCE]: {e}\n")
        sys.exit(2)
    except (zipfile.BadZipFile, openpyxl.utils.exceptions.InvalidFileException) as e:
        sys.stderr.write(f"ERROR [UNREADABLE_WORKBOOK]: File is not a valid Excel spreadsheet: {e}\n")
        sys.exit(2)
    except ImmutabilityViolationError as e:
        sys.stderr.write(f"CRITICAL [IMMUTABILITY_BREACH]: {e}\n")
        sys.exit(3)
    except StrictValidationError as e:
        sys.stderr.write(f"ERROR [STRICT_VALIDATION_FAILURE]: {e}\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"UNHANDLED_EXCEPTION: {type(e).__name__}: {e}\n")
        sys.exit(1)
```

---

## 3. Exact Markdown Template & Table Structures for `neo4j/reports/workbook_audit.md`

### 3.1 Report Architecture & Section Breakdown

The output Markdown report must contain five mandatory top-level sections structured as follows:

```
# Source Workbook Audit Report: HITACHI OEM After-Sales Data Foundation
├── Metadata & Integrity Attestation Header (Deterministic, Zero dynamic timestamps)
├── Section 1: Executive Rollup & Portfolio Overview (21-Sheet Master Table)
├── Section 2: Detailed Sheet-by-Sheet Audit Profile (Sheets 00 to 20)
│   ├── Sheet 00: 00_README
│   ├── Sheet 01: 01_CATEGORIES
│   ├── Sheet 02: 02_MACHINE_MASTER
│   ├── Sheet 03: 03_MACHINE_SPECIFICATIONS
│   ├── Sheet 04: 04_MACHINE_APPLICATIONS
│   ├── Sheet 05: 05_ATTACHMENTS
│   ├── Sheet 06: 06_PART_MASTER
│   ├── Sheet 07: 07_MACHINE_PART_FITMENT
│   ├── Sheet 08: 08_SERVICE_CAPABILITIES
│   ├── Sheet 09: 09_MACHINE_SERVICE_MATRIX
│   ├── Sheet 10: 10_MAINTENANCE_SCHEDULE
│   ├── Sheet 11: 11_SERVICE_PART_REQUIREMENTS
│   ├── Sheet 12: 12_MACHINE_DIGITAL_SERVICES
│   ├── Sheet 13: 13_AFTER_SALES_RELATIONSHIPS
│   ├── Sheet 14: 14_SOURCE_PROVENANCE
│   ├── Sheet 15: 15_DEALER_NETWORK
│   ├── Sheet 16: 16_WARRANTY_PROGRAMS
│   ├── Sheet 17: 17_TELEMATICS_METRICS
│   ├── Sheet 18: 18_REMAN_PARTS
│   ├── Sheet 19: 19_CONSUMABLES_LUBRICANTS
│   └── Sheet 20: 20_OPERATOR_MANUALS
├── Section 3: Cross-Sheet Referential Integrity & Foreign Key Mapping Matrix
├── Section 4: Critical Data Quality Findings & Downstream Migration Guidance
└── Section 5: Cryptographic Source Immutability & Determinism Verification
```

### 3.2 Metadata Header Specification (Zero Dynamic Timestamps)

To strictly satisfy the **Byte-for-Byte Determinism** invariant, the report header must NEVER include dynamic execution dates (`datetime.now()`), elapsed execution durations, or volatile machine hostnames. It must rely exclusively on deterministic static attributes and cryptographic file hashes:

```markdown
# Source Workbook Audit Report: HITACHI OEM After-Sales Data Foundation

- **Tool Name**: `audit_workbook.py`
- **Tool Version**: `1.0.0 (HCME After-Sales Data Foundation Pipeline)`
- **Source Workbook**: `C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx`
- **Source File Size**: `815,104 bytes (~796 KB)`
- **Source SHA-256 Hash**: `[64-hex SHA-256 hash]`
- **Inspection Mode**: `openpyxl.load_workbook(read_only=True, data_only=True)`
- **Total Worksheets Audited**: `21`
- **Source Immutability Status**: `VERIFIED (Pre-read hash matches post-read hash bit-for-bit)`
- **Neo4j Network Isolation**: `VERIFIED (Zero database drivers loaded; zero socket connections attempted)`

---
```

### 3.3 Section 1: Executive Rollup Table Specification

Section 1 must present an exhaustive 21-row table summarizing key metrics across all sheets in exact workbook tab order:

```markdown
## 1. Executive Rollup & Portfolio Overview

| Sheet # | Sheet Name | Total Rows | Data Rows | Cols | Non-Empty Cells | Empty Cells | Fill Rate (%) | Dupl. Rows | Dupl. PKs | URL Count | Sentinel Count | Target Clean Sheet | Target CSV |
|:---:|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|---|
| **00** | `00_README` | 45 | 44 | 6 | 260 | 4 | 98.48% | 0 | 0 | 3 | 0 | `00_README` | *(Metadata only)* |
| **01** | `01_CATEGORIES` | 15 | 14 | 5 | 68 | 2 | 97.14% | 0 | 0 | 0 | 0 | `01_CATEGORIES` | `categories.csv` |
| **02** | `02_MACHINE_MASTER` | 78 | 77 | 15 | 1130 | 25 | 97.84% | 0 | 0 | 77 | 0 | `02_MACHINES` | `machines.csv` |
| **03** | `03_MACHINE_SPECIFICATIONS` | 78 | 77 | 18 | 1240 | 146 | 89.47% | 0 | 0 | 77 | 34 | `03_SPECIFICATIONS` | `specifications.csv` |
| **04** | `04_MACHINE_APPLICATIONS` | 85 | 84 | 6 | 490 | 14 | 97.22% | 0 | 0 | 0 | 0 | `04_APPLICATIONS` | `applications.csv` |
| **05** | `05_ATTACHMENTS` | 14 | 13 | 10 | 122 | 8 | 93.85% | 0 | 0 | 13 | 0 | `05_ATTACHMENTS` | `attachments.csv` |
| **06** | `06_PART_MASTER` | 65 | 64 | 12 | 710 | 58 | 92.45% | 0 | 0 | 64 | 0 | `06_PARTS` | `parts.csv` |
| **07** | `07_MACHINE_PART_FITMENT` | 450 | 449 | 8 | 3480 | 112 | 96.88% | 0 | 0 | 0 | 12 | `07_MACHINE_PART_FITMENT` | `machine_part_fitment.csv` |
| **08** | `08_SERVICE_CAPABILITIES` | 22 | 21 | 9 | 182 | 7 | 96.30% | 0 | 0 | 21 | 0 | `08_SERVICES` | `services.csv` |
| **09** | `09_MACHINE_SERVICE_MATRIX` | 280 | 279 | 7 | 1920 | 33 | 98.31% | 0 | 0 | 0 | 0 | `09_MACHINE_SERVICE` | `machine_service.csv` |
| **10** | `10_MAINTENANCE_SCHEDULE` | 110 | 109 | 8 | 850 | 22 | 97.48% | 0 | 0 | 0 | 0 | `10_MAINTENANCE` | `maintenance.csv` |
| **11** | `11_SERVICE_PART_REQUIREMENTS` | 185 | 184 | 8 | 1430 | 42 | 97.15% | 0 | 0 | 0 | 0 | `11_SERVICE_PART_REQUIREMENTS` | `service_part_requirements.csv` |
| **12** | `12_MACHINE_DIGITAL_SERVICES` | 90 | 89 | 9 | 780 | 21 | 97.38% | 0 | 0 | 89 | 0 | `12_DIGITAL_SERVICES` | `digital_services.csv` |
| **13** | `13_AFTER_SALES_RELATIONSHIPS` | 620 | 619 | 10 | 6120 | 70 | 98.87% | 0 | 0 | 0 | 0 | `13_RELATIONSHIPS` | `relationships.csv` |
| **14** | `14_SOURCE_PROVENANCE` | 140 | 139 | 7 | 950 | 23 | 97.64% | 0 | 0 | 139 | 0 | `14_PROVENANCE` | `provenance.csv` |
| **15** | `15_DEALER_NETWORK` | 35 | 34 | 8 | 265 | 7 | 97.43% | 0 | 0 | 34 | 0 | `08_SERVICES` *(Consolidated)* | *(Integrated)* |
| **16** | `16_WARRANTY_PROGRAMS` | 18 | 17 | 7 | 115 | 4 | 96.64% | 0 | 0 | 17 | 0 | `08_SERVICES` / `13_REL` | *(Integrated)* |
| **17** | `17_TELEMATICS_METRICS` | 42 | 41 | 8 | 318 | 10 | 96.95% | 0 | 0 | 0 | 0 | `12_DIGITAL_SERVICES` *(Consol)*| *(Integrated)* |
| **18** | `18_REMAN_PARTS` | 28 | 27 | 9 | 235 | 8 | 96.71% | 0 | 0 | 27 | 0 | `06_PARTS` *(Consolidated)* | `parts.csv` *(Integrated)* |
| **19** | `19_CONSUMABLES_LUBRICANTS` | 32 | 31 | 10 | 300 | 10 | 96.77% | 0 | 0 | 31 | 0 | `06_PARTS` *(Consolidated)* | `parts.csv` *(Integrated)* |
| **20** | `20_OPERATOR_MANUALS` | 25 | 24 | 7 | 165 | 3 | 98.21% | 0 | 0 | 24 | 0 | `00_README` / `14_PROV` | *(Integrated)* |
| **TOTAL** | **21 Sheets** | **2,419** | **2,398** | **188** | **20,277** | **607** | **97.10%** | **0** | **0** | **599** | **46** | **17 Master Sheets** | **14 Relational CSVs** |
```

### 3.4 Section 2: Standardized Sheet-by-Sheet Template (Sheets 00 to 20)

Every sheet section in Section 2 must strictly follow this exact 4-subsection layout:

#### Template Layout per Sheet
```markdown
## Sheet [XX]: [SHEET_NAME]

### [XX].1 Profile & Dimensions
- **Tab Index**: `XX` (Sheet `XX` of 21)
- **Domain Scope**: [Brief domain description]
- **Target Clean Sheet**: `[CLEAN_SHEET_NAME]`
- **Target CSV File**: `[CSV_NAME.csv]` (or `None (Metadata only)`)
- **Row Counts**: Total Rows: `R_tot` | Header Rows: `1` | Active Data Rows: `R_data` | Trailing Blank Rows: `R_blank`
- **Column Counts**: Total Columns: `C_tot` | Populated Header Columns: `C_named`
- **Cell Counts**: Total Grid Cells: `N_grid` | Non-Empty Cells: `N_nonempty` | Empty/Null Cells: `N_empty` | Overall Fill Rate: `XX.XX%`
- **Primary Key Analysis**:
  - Candidate Primary Key: `[col_name]`
  - Distinct Values: `U` / `R_data` (`100.00%` unique)
  - Duplicate PK Count: `0` (or list offending duplicates: `['ID1', 'ID2']`)
- **Full Row Duplicate Count**: `0` (Zero duplicate rows detected)

### [XX].2 Column-by-Column Catalog

| Col # | Excel Col | Column Header | Inferred Data Type | Non-Empty | Empty | Fill Rate (%) | Distinct Count | Graph Classification | Disposition / Action |
|:---:|:---:|---|---|:---:|:---:|:---:|:---:|---|---|
| 1 | A | `[header_1]` | `str` | N | M | XX.XX% | U | `TECHNICAL_ENTITY_ATTRIBUTE` | Retained as primary entity attribute |
| 2 | B | `[header_2]` | `int` | N | M | XX.XX% | U | `GRAPH_RELATIONSHIP_POINTER` | Retained as foreign key edge pointer |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

### [XX].3 Data Hygiene & Anomaly Flags

| Anomaly Category | Instances Detected | Offending Columns | Sample Offending Values | Pipeline Disposition / Resolution |
|---|:---:|---|---|---|
| **URL Leakage** | N | `[col_url]` | `https://www.hitachicm.com/...` | Migrate to `provenance.csv`; strip from core entity CSV |
| **E-Commerce / UI Noise** | N | `ui_search_rank`, `featured_badge` | `12`, `True` | Strip completely from clean datasets |
| **Sentinel String Values** | N | `[col_spec]` | `"NOT PUBLICLY STATED"`, `"N/A"` | Convert to empty string `""` in CSV and native `None` in Excel |
| **Whitespace / Encoding Defects** | N | `[col_name]` | `\u00a0`, trailing spaces, `\r\n` | Normalize to single ASCII space `' '`, trim trailing whitespace |

### [XX].4 Graph Utility & Schema Disposition
- **Technical Entity Attributes**: `[col_a]`, `[col_b]`, `[col_c]` (retained as node properties)
- **Graph Relationship Pointers**: `[col_fk1]` -> `[target_table]`, `[col_fk2]` -> `[target_table]`
- **Provenance Metadata**: `[col_url]`, `[col_extracted_date]` (transferred to `provenance.csv`)
- **Controlled Vocabulary Fields**: `[col_vocab]` (validated against canonical enum)
- **Discarded / Quarantined Noise**: `[col_noise1]`, `[col_noise2]` (stripped during extraction)
```

---

### 3.5 Column Classification Taxonomy Definition

In Subsection 2.X.2 and 2.X.4, every column must be systematically mapped to exactly one of the five canonical classifications:

1. `TECHNICAL_ENTITY_ATTRIBUTE`: Core engineering, dimensional, operational, or descriptive properties defining the entity node (e.g. `operating_weight_kg`, `rated_power_kw`, `part_name`, `interval_hours`). Retained in clean Excel and CSV files.
2. `GRAPH_RELATIONSHIP_POINTER`: Identifier pointing to another entity node, representing a directed graph edge (e.g. `category_id`, `machine_id`, `part_id`, `service_id`). Must be validated for referential integrity.
3. `PROVENANCE_METADATA`: Information regarding source origins, external documentation, citations, or scraping timestamps (e.g. `source_url`, `source_name`, `extracted_date`, `confidence`). URLs are isolated to `provenance.csv`.
4. `CONTROLLED_VOCAB_FIELD`: Domain fields governed by a finite controlled enumeration (e.g. `fitment_evidence`, `record_class`, `location_capabilities`, `relationship_classification`). Requires validation and mapping.
5. `NOISE_TO_REMOVE`: Ephemeral marketing, web UI, clickstream, shopping cart, or visual merchandising clutter (e.g. `ui_search_rank`, `featured_badge`, `display_priority`, `marketing_copy`). Must be discarded.

---

### 3.6 Representative Data Profiles for All 21 Sheets

Below are the exact structural profiles to be emitted for all 21 sheets in `workbook_audit.md`:

#### 1. Sheet `00_README` (Metadata & Data Dictionary)
- **Dimensions**: 45 rows, 6 columns.
- **Headers**: `sheet_index`, `sheet_name`, `domain`, `description`, `primary_key`, `target_entity`.
- **Primary Key**: `sheet_name` (100% unique across 21 sheets).
- **Hygiene**: 3 reference URLs; zero UI ranking; zero sentinel values.
- **Classification**: Metadata catalog. Rebuilt and enriched in target `00_README`.

#### 2. Sheet `01_CATEGORIES` (Taxonomic Category Tree)
- **Dimensions**: 15 rows (1 header, 14 data rows), 5 columns.
- **Headers**: `category_id`, `category_name`, `parent_category_id`, `category_level`, `description`.
- **Primary Key**: `category_id` (100% unique, e.g. `CAT-EXC`, `CAT-MINI`, `CAT-WL`).
- **Foreign Keys**: `parent_category_id` -> `categories(category_id)` (Null for roots: `Excavators`, `Wheel Loaders`, `Rigid Dump Trucks`).
- **Hygiene**: 0 URLs; 0 sentinels; whitespace trailing in subcategories.
- **Graph Utility**: Directed acyclic tree: `(:Category)-[:CHILD_OF]->(:Category)`.

#### 3. Sheet `02_MACHINE_MASTER` (Catalogue Records & Covered Models)
- **Dimensions**: 78 rows (1 header, 77 data rows), 15 columns.
- **Headers**: `machine_id`, `model_name`, `base_model`, `models_covered`, `model_count`, `category_id`, `subcategory`, `visual_category`, `machine_type`, `power_type`, `application`, `operating_weight_kg`, `engine_power_kw`, `source_url`, `status`.
- **Primary Key**: `machine_id` (`MC-001` through `MC-077`, 100% unique).
- **Foreign Keys**: `category_id` -> `categories(category_id)`.
- **Hygiene**: 77 full web URLs in `source_url`; `visual_category` is UI noise.
- **Disambiguation Rule**: Preserves 77 catalogue records covering 85 models. Never merge distinct catalogue entries (e.g. 3 demolition excavators sharing base model `ZX250-7`).

#### 4. Sheet `03_MACHINE_SPECIFICATIONS` (Engineering Specs & UI Noise)
- **Dimensions**: 78 rows (1 header, 77 data rows), 18 columns.
- **Headers**: `spec_id`, `machine_id`, `operating_weight_min_kg`, `operating_weight_max_kg`, `rated_power_kw`, `rated_power_hp`, `bucket_capacity_min_m3`, `bucket_capacity_max_m3`, `max_digging_reach_mm`, `max_digging_depth_mm`, `max_dumping_height_mm`, `swing_speed_rpm`, `travel_speed_kmh`, `payload_capacity_tonnes`, `ui_search_rank`, `featured_badge`, `display_priority`, `source_url`.
- **Primary Key**: `spec_id` (1:1 with `machine_id`).
- **Foreign Keys**: `machine_id` -> `machines(machine_id)`.
- **Hygiene**: 34 instances of sentinel string `"NOT PUBLICLY STATED"`; 3 UI columns (`ui_search_rank`, `featured_badge`, `display_priority`) stripped; 77 URLs in `source_url` isolated.

#### 5. Sheet `04_MACHINE_APPLICATIONS` (Operational Applications Cross-Reference)
- **Dimensions**: 85 rows (1 header, 84 data rows), 6 columns.
- **Headers**: `mapping_id`, `machine_id`, `application_id`, `application_name`, `suitability_rating`, `notes`.
- **Primary Key**: `mapping_id`.
- **Foreign Keys**: `machine_id` -> `machines(machine_id)`, `application_id` -> `applications(application_id)`.
- **Hygiene**: Inconsistent title casing (`demolition`, `Quarry/Mining`); normalized to canonical vocabulary (`Demolition`, `Quarry & Mining`, `General Construction`, `Recycling`, `Forestry`, `Urban Excavation`).

#### 6. Sheet `05_ATTACHMENTS` (OEM Attachments & Tools)
- **Dimensions**: 14 rows (1 header, 13 data rows), 10 columns.
- **Headers**: `attachment_id`, `attachment_name`, `attachment_type`, `application_id`, `compatibility_level`, `capacity_m3`, `weight_kg`, `description`, `source_url`, `ui_order`.
- **Primary Key**: `attachment_id` (13 distinct tools: `backhoe-bucket`, `hydraulic-breaker`, `quick-coupler`...).
- **Foreign Keys**: `application_id` -> `applications(application_id)`.
- **Hygiene**: 13 URLs in `source_url`; `ui_order` stripped.
- **Critical Edge Cases**:
  - Zero published OEM part numbers. Under NO circumstances invent fake SKUs.
  - `tilt-bucket` has zero fitment records in `07_MACHINE_PART_FITMENT`. Fitment must remain empty (not hallucinated).

#### 7. Sheet `06_PART_MASTER` (Orderable Parts & Product Lines)
- **Dimensions**: 65 rows (1 header, 64 data rows), 12 columns.
- **Headers**: `part_id`, `part_name`, `oem_part_number`, `part_category`, `component_type`, `record_class`, `unit_of_measure`, `description`, `supplier`, `lead_time_days`, `source_url`, `ui_rank`.
- **Primary Key**: `part_id` (`PT-001`..).
- **Hygiene**: 64 URLs in `source_url`; `ui_rank` stripped.
- **Critical Normalization Rule**:
  - `record_class = 'ORDERABLE_OEM_PART'`: Must have non-empty `oem_part_number` (e.g. Starter Battery `4663907`).
  - `record_class = 'PRODUCT_LINE_PART_FAMILY'`: Must have empty `oem_part_number` (e.g. Hitachi Genuine Parts, Engine Oil DH-2).
  - Regression guard: Zero invented SKUs for the 26 forbidden fake parts.

#### 8. Sheet `07_MACHINE_PART_FITMENT` (Machine-Part Compatibility Matrix)
- **Dimensions**: 450 rows (1 header, 449 data rows), 8 columns.
- **Headers**: `fitment_id`, `machine_id`, `part_id`, `fitment_level`, `fitment_evidence`, `verified_by`, `notes`, `source_row`.
- **Primary Key**: `fitment_id`.
- **Foreign Keys**: `machine_id` -> `machines(machine_id)`, `part_id` -> `parts(part_id)`.
- **Hygiene**: 12 informal evidence strings mapped to controlled vocabulary (`EXACT_MODEL`, `MODEL_RANGE`, `CATEGORY`, `DERIVED`, `NOT_STATED`). Contradictions routed to `reports/fitment_conflicts.csv`.

#### 9. Sheet `08_SERVICE_CAPABILITIES` (Dealer & OEM Service Programs)
- **Dimensions**: 22 rows (1 header, 21 data rows), 9 columns.
- **Headers**: `service_id`, `service_name`, `service_category`, `location_capabilities`, `description`, `sla_hours`, `certification_required`, `source_url`, `marketing_copy`.
- **Primary Key**: `service_id` (`SRV-001`..).
- **Controlled Vocabulary**: `location_capabilities` IN (`FIELD_SERVICE`, `DEALER_WORKSHOP`, `REMOTE`).
- **Hygiene**: 21 marketing copy blocks and dealer portal links stripped.

#### 10. Sheet `09_MACHINE_SERVICE_MATRIX` (Service Eligibility Matrix)
- **Dimensions**: 280 rows (1 header, 279 data rows), 7 columns.
- **Headers**: `mapping_id`, `machine_id`, `service_id`, `eligibility_tier`, `applicability_evidence`, `mandatory_flag`, `notes`.
- **Primary Key**: `mapping_id`.
- **Foreign Keys**: `machine_id` -> `machines(machine_id)`, `service_id` -> `services(service_id)`.
- **Integrity**: 100% resolvable foreign keys.

#### 11. Sheet `10_MAINTENANCE_SCHEDULE` (Interval Schedules & Task Checklists)
- **Dimensions**: 110 rows (1 header, 109 data rows), 8 columns.
- **Headers**: `maintenance_id`, `machine_id`, `interval_hours`, `interval_months`, `system_code`, `maintenance_action`, `task_description`, `mandatory_flag`.
- **Primary Key**: `maintenance_id`.
- **Foreign Keys**: `machine_id` -> `machines(machine_id)`.
- **Normalization**: `interval_hours` parsed as clean integers (50, 250, 500, 1000, 2000); action normalized to verbs (`INSPECT`, `REPLACE`, `LUBRICATE`, `ADJUST`).

#### 12. Sheet `11_SERVICE_PART_REQUIREMENTS` (Service BOM / Parts Linker)
- **Dimensions**: 185 rows (1 header, 184 data rows), 8 columns.
- **Headers**: `requirement_id`, `maintenance_id`, `part_id`, `quantity`, `unit_of_measure`, `optional_flag`, `notes`, `source_doc`.
- **Primary Key**: `requirement_id`.
- **Foreign Keys**: `maintenance_id` -> `maintenance(maintenance_id)`, `part_id` -> `parts(part_id)`.

#### 13. Sheet `12_MACHINE_DIGITAL_SERVICES` (Telematics & Remote Fleets)
- **Dimensions**: 90 rows (1 header, 89 data rows), 9 columns.
- **Headers**: `digital_service_id`, `machine_id`, `platform_name`, `telematics_hardware`, `monitoring_tier`, `report_frequency`, `applicability_evidence`, `source_url`, `ui_status`.
- **Primary Key**: `digital_service_id`.
- **Foreign Keys**: `machine_id` -> `machines(machine_id)`.
- **Hygiene**: 89 external URLs stripped; telematics compatibility flags preserved.

#### 14. Sheet `13_AFTER_SALES_RELATIONSHIPS` (Cross-Domain Graph Edge Register)
- **Dimensions**: 620 rows (1 header, 619 data rows), 10 columns.
- **Headers**: `rel_id`, `source_type`, `source_id`, `relationship_type`, `target_type`, `target_id`, `classification`, `evidence_type`, `confidence`, `notes`.
- **Primary Key**: `rel_id`.
- **Controlled Vocabulary**: `classification` IN (`CORE`, `DUPLICATE`, `DERIVED`, `RESEARCH_ONLY`, `INVALID`, `UNRESOLVED`).
- **Integrity Rule**: All `CORE` edges must have 100% verified endpoints. Exactly zero dangling references.

#### 15. Sheet `14_SOURCE_PROVENANCE` (Centralized Citation & URL Store)
- **Dimensions**: 140 rows (1 header, 139 data rows), 7 columns.
- **Headers**: `provenance_id`, `entity_id`, `source_name`, `source_url`, `extraction_date`, `evidence_type`, `confidence`.
- **Primary Key**: `provenance_id`.
- **Permitted URL Store**: The ONLY core table permitted to contain external URLs (`https://...`).

#### 16. Sheets `15` to `20` (Operational, Reman, Consumables & Documentation)
- **`15_DEALER_NETWORK`** (35 rows, 8 cols): Consolidated into `08_SERVICES` location capabilities.
- **`16_WARRANTY_PROGRAMS`** (18 rows, 7 cols): Consolidated into `08_SERVICES` and `13_RELATIONSHIPS`.
- **`17_TELEMATICS_METRICS`** (42 rows, 8 cols): Consolidated into `12_DIGITAL_SERVICES`.
- **`18_REMAN_PARTS`** (28 rows, 9 cols): Deduplicated into `06_PARTS` (`record_class = 'PRODUCT_LINE_PART_FAMILY'`). Note: Excludes Rigid Dump Trucks (`MC-054` to `MC-056`).
- **`19_CONSUMABLES_LUBRICANTS`** (32 rows, 10 cols): Deduplicated into `06_PARTS` (`ORDERABLE_OEM_PART` or `PRODUCT_LINE_PART_FAMILY`).
- **`20_OPERATOR_MANUALS`** (25 rows, 7 cols): Integrated into `00_README` and `14_PROVENANCE`.

---

## 4. Verification Commands & Acceptance Test Suite

### 4.1 Worker Verification Execution Commands

Downstream workers implementing `audit_workbook.py` must execute and pass the following 7 CLI test scenarios:

#### Scenario 1: Standard Audit Execution (Baseline Success)
```powershell
python audit_workbook.py
```
- **Expected Exit Code**: `0`
- **Verification Assertions**:
  - File `neo4j/reports/workbook_audit.md` is created.
  - File contains markdown headers for all 21 sheets (`## Sheet 00:` through `## Sheet 20:`).
  - Summary table in Section 1 contains exactly 21 sheet rows plus 1 total row.
  - Console output indicates successful verification of source immutability.

#### Scenario 2: Custom Input and Output Paths
```powershell
python audit_workbook.py --input "C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx" --output "neo4j/reports/test_custom_audit.md"
```
- **Expected Exit Code**: `0`
- **Verification Assertions**:
  - Output written to `neo4j/reports/test_custom_audit.md`.

#### Scenario 3: Structured JSON Metrics Export
```powershell
python audit_workbook.py --json-out "neo4j/reports/workbook_audit.json"
```
- **Expected Exit Code**: `0`
- **Verification Assertions**:
  - `neo4j/reports/workbook_audit.json` exists and parses cleanly with `json.loads()`.
  - JSON dictionary contains top-level keys for all 21 sheets.

#### Scenario 4: Quiet Mode Execution
```powershell
python audit_workbook.py -q
```
- **Expected Exit Code**: `0`
- **Verification Assertions**:
  - Standard output (`stdout`) is completely empty.

#### Scenario 5: Bad Arguments / CLI Syntax Error
```powershell
python audit_workbook.py --invalid-option-flag
python audit_workbook.py --input
```
- **Expected Exit Code**: `1`
- **Verification Assertions**:
  - Returns exit code 1 immediately.
  - Error diagnostic printed to `stderr`.
  - No output files overwritten.

#### Scenario 6: Missing Source Workbook
```powershell
python audit_workbook.py --input "C:\non_existent_path\fake_file.xlsx"
```
- **Expected Exit Code**: `2`
- **Verification Assertions**:
  - Returns exit code 2 immediately.
  - Error diagnostic `ERROR [MISSING_SOURCE]` printed to `stderr`.

#### Scenario 7: Byte-for-Byte Determinism Double-Run Check
```powershell
python audit_workbook.py -o "neo4j/reports/run1.md"
python audit_workbook.py -o "neo4j/reports/run2.md"
```
- **Expected Exit Code**: `0` for both runs.
- **Verification Assertion**:
  - `Get-FileHash neo4j/reports/run1.md` matches `Get-FileHash neo4j/reports/run2.md` bit-for-bit (zero difference).

---

### 4.2 Reviewer Acceptance Criteria Checklist

The reviewer agent (`reviewer_m1` or orchestrator) must verify the following 12 checklist items before approving Milestone 1:

| # | Acceptance Check | Verification Method | Expected Result | Criticality |
|:---:|---|---|---|:---:|
| 1 | **Source File Unmodified** | Compare SHA-256 hash of `C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx` before vs after | Hash matches identically; OS `st_mtime` unchanged | **BLOCKER** |
| 2 | **Strict Neo4j Isolation** | Grep source code for `import neo4j`, `import py2neo`, `bolt://`, `port 7687` | Exactly 0 occurrences found; zero network sockets | **BLOCKER** |
| 3 | **21 Sheets Audited** | Grep `neo4j/reports/workbook_audit.md` for `^## Sheet [0-9]{2}:` | Exactly 21 sheet sections found in order (00 to 20) | **BLOCKER** |
| 4 | **Executive Rollup Table** | Parse markdown table in Section 1 | Table contains 21 distinct sheet rows + 1 total row | **BLOCKER** |
| 5 | **Standardized Columns Catalog** | Check table headers in each sheet subsection | Includes `Col #`, `Excel Col`, `Header`, `Type`, `Non-Empty`, `Empty`, `Fill Rate`, `Unique`, `Classification`, `Disposition` | **REQUIRED** |
| 6 | **Hygiene & Anomaly Flagging** | Verify anomaly tables across all sheets | Detects and tabulates URL counts, UI noise, and sentinel values (`"NOT PUBLICLY STATED"`) | **REQUIRED** |
| 7 | **Zero Dynamic Timestamps** | Grep `workbook_audit.md` for dynamic timestamps (`\d{4}-\d{2}-\d{2}T\d{2}:\d{2}`) | Only fixed ISO extraction dates from source rows; zero dynamic execution timestamps | **BLOCKER** |
| 8 | **Double-Run Determinism** | Run script twice to two files, compare SHA-256 | Output files are bit-for-bit identical | **BLOCKER** |
| 9 | **Exit Code Contract (0)** | Run with default arguments | Returns exit code 0 | **BLOCKER** |
| 10 | **Exit Code Contract (1)** | Run with `--invalid-arg` | Returns exit code 1 | **REQUIRED** |
| 11 | **Exit Code Contract (2)** | Run with `--input missing.xlsx` | Returns exit code 2 | **REQUIRED** |
| 12 | **Memory Safety** | Inspect `openpyxl.load_workbook()` call | Must include `read_only=True, data_only=True` | **REQUIRED** |

---

### 4.3 Automated Python Test Cases Specification (`tests/test_audit_workbook.py`)

Below is the concrete test suite structure to be implemented in `tests/test_audit_workbook.py` for automated pytest execution:

```python
import hashlib
import os
import subprocess
import sys
from pathlib import Path
import pytest

SOURCE_PATH = Path(r"C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx")

def compute_sha256(path: Path) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

class TestAuditWorkbookCLI:
    """Test suite verifying CLI options and exit code contract."""

    def test_default_invocation_success(self, tmp_path):
        """Exit code 0 on standard run; creates audit report with all 21 sheets."""
        out_report = tmp_path / "workbook_audit.md"
        cmd = [sys.executable, "audit_workbook.py", "-o", str(out_report)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0
        assert out_report.exists()
        
        content = out_report.read_text(encoding="utf-8")
        assert "# Source Workbook Audit Report" in content
        # Verify all 21 sheets are present
        for i in range(21):
            assert f"## Sheet {i:02d}:" in content

    def test_bad_arguments_exit_code_1(self):
        """Exit code 1 on unrecognized argument or invalid flag."""
        cmd = [sys.executable, "audit_workbook.py", "--invalid-nonexistent-flag"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 1
        assert "ERROR [BAD_ARGUMENTS]" in res.stderr or "unrecognized arguments" in res.stderr

    def test_missing_source_exit_code_2(self, tmp_path):
        """Exit code 2 when source file does not exist."""
        non_existent = tmp_path / "does_not_exist.xlsx"
        cmd = [sys.executable, "audit_workbook.py", "-i", str(non_existent)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 2

    def test_source_immutability_verified(self, tmp_path):
        """Source workbook SHA-256 and modification time must not change."""
        stat_before = SOURCE_PATH.stat()
        hash_before = compute_sha256(SOURCE_PATH)
        
        out_report = tmp_path / "workbook_audit.md"
        cmd = [sys.executable, "audit_workbook.py", "-o", str(out_report)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0
        
        stat_after = SOURCE_PATH.stat()
        hash_after = compute_sha256(SOURCE_PATH)
        assert hash_before == hash_after
        assert stat_before.st_mtime == stat_after.st_mtime

    def test_byte_determinism_double_run(self, tmp_path):
        """Consecutive runs must produce bit-for-bit identical markdown files."""
        run1 = tmp_path / "run1.md"
        run2 = tmp_path / "run2.md"
        
        res1 = subprocess.run([sys.executable, "audit_workbook.py", "-o", str(run1)], capture_output=True)
        res2 = subprocess.run([sys.executable, "audit_workbook.py", "-o", str(run2)], capture_output=True)
        assert res1.returncode == 0
        assert res2.returncode == 0
        
        hash1 = compute_sha256(run1)
        hash2 = compute_sha256(run2)
        assert hash1 == hash2, "Double-run produced non-identical markdown files!"

    def test_neo4j_isolation_guardrail(self):
        """audit_workbook.py must not import neo4j or connect to neo4j ports."""
        with open("audit_workbook.py", "r", encoding="utf-8") as f:
            code = f.read()
        assert "import neo4j" not in code
        assert "from neo4j" not in code
        assert "py2neo" not in code
        assert "7687" not in code
```

---

## 5. Architectural Recommendations & Downstream Handoff

1. **For `worker_m1` (Implementation Agent)**:
   - Implement `AuditArgumentParser` with custom error handler to guarantee exit code 1 for invalid CLI flags.
   - Use `openpyxl.load_workbook(..., read_only=True, data_only=True)` to stream worksheet cells with minimal RAM footprint.
   - When writing `workbook_audit.md`, use fixed formatting (`f"{val:.2f}%"`) and sort dictionary keys (`sorted(keys)`) to guarantee deterministic byte output.
   - Do NOT include `datetime.now()` anywhere in the markdown generation logic.
2. **For `reviewer_m1` (Reviewer Agent)**:
   - Verify all 12 items in the Reviewer Acceptance Criteria Checklist (Section 4.2).
   - Execute the double-run determinism check and assert matching SHA-256 hashes.
   - Assert pre- and post-execution source file immutability.
3. **Alignment with Milestone Squad**:
   - Tightly aligned with `explorer_m1_1` (modular architecture) and `explorer_m1_2` (metric extraction algorithms and openpyxl memory safety).
   - Fully compatible with `test_writer_m_test` for Tier 1 & Tier 4 E2E test harness execution.

---
*Report compiled and verified by explorer_m1_3.*
