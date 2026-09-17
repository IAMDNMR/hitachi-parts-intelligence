# Source Audit Engine Specification: Data Structures, Metric Extraction & Determinism Controls

**Agent**: `explorer_m1_2` (Explorer: Source Immutability & Audit Metrics)  
**Milestone**: Milestone 1 (Discovery & Source Audit)  
**Target Script**: `audit_workbook.py`  
**Target Report**: `neo4j/reports/workbook_audit.md`  
**Status**: COMPLETE — AUTHORITATIVE SPECIFICATION  

---

## 1. Executive Summary

This specification defines the computational data structures, metric extraction algorithms, openpyxl memory safety protocols, and 100% byte-level determinism controls for `audit_workbook.py`.

As established in `ORIGINAL_REQUEST.md`, `PROJECT.md`, and previous survey reports (`spec_miner_survey_1`, `explorer_survey_2`, `explorer_survey_3`), the raw source file `HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx` (21 sheets, ~796 KB) must undergo a comprehensive, non-destructive pre-cleaning audit.

### 1.1 Non-Negotiable Architectural Constraints
1. **Source Immutability**: The source file must remain completely untouched. Pre- and post-execution SHA-256 hashes and file modification timestamps (`st_mtime_ns`) must be verified bit-for-bit identical.
2. **Strict Neo4j Isolation Guardrail**: Under NO circumstances connect to Neo4j, call Neo4j Aura, or import database drivers. Work strictly terminates with verified reports on disk.
3. **Memory Safety via Read-Only Streaming**: Must use `openpyxl.load_workbook(path, read_only=True, data_only=True)` with explicit generator streaming to minimize memory footprint and prevent RAM inflation.
4. **100% Byte-Level Determinism**: Successive runs of `audit_workbook.py` must produce byte-identical markdown reports. This mandates the elimination of all dynamic timestamps (`datetime.now()`), fixed float precision formatting, deterministic dictionary and list sorting, and LF (`\n`) line endings.

---

## 2. In-Memory Data Structures for Audit Metrics

To cleanly encapsulate audit metrics without polluting global scope, `audit_workbook.py` must define strongly-typed data structures using Python standard library `dataclasses`.

```python
"""
Data structures for audit_workbook.py
"""
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Any
from collections import Counter


@dataclass
class ColumnAuditMetrics:
    """Detailed audit metrics for a single column within a sheet."""
    col_idx: int                      # 1-based column index
    col_letter: str                   # Excel column letter ('A', 'B', ...)
    header: str                       # Normalized header string
    raw_header: Optional[str]         # Verbatim raw header as read from cell
    inferred_types: Set[str] = field(default_factory=set)  # {'str', 'int', 'float', 'datetime', 'NoneType'}
    total_cells: int = 0              # Total evaluated data cells (rows)
    non_empty_count: int = 0          # Cells with non-blank, non-null values
    empty_count: int = 0              # Cells where value is None or blank whitespace
    fill_rate: float = 0.0            # (non_empty_count / total_cells) * 100
    cardinality: int = 0              # Count of distinct non-null values
    sample_values: List[str] = field(default_factory=list) # Deterministic sample of distinct values
    url_count: int = 0                # Cells matching URL patterns
    sentinel_count: int = 0           # Cells matching sentinel strings ("NOT PUBLICLY STATED", "N/A", "-")
    sentinel_breakdown: Counter = field(default_factory=Counter) # Exact counts per sentinel string
    whitespace_issues_count: int = 0  # Cells with \u00a0, leading/trailing spaces, or internal newlines
    utility_classification: str = "TECHNICAL_ENTITY_ATTRIBUTE" # 5-class taxonomy
    classification_rationale: str = "" # Short explanation for classification


@dataclass
class SheetAuditMetrics:
    """Comprehensive audit metrics for an individual worksheet."""
    sheet_index: int                  # 1-based sheet position in workbook (1..21)
    sheet_name: str                   # Exact sheet name
    raw_row_count: int = 0            # Total rows streamed including blank rows
    header_row_index: int = 1         # Row containing headers (normally 1)
    data_row_count: int = 0           # Active rows containing at least one non-empty cell
    empty_row_count: int = 0          # Entirely blank rows
    raw_col_count: int = 0            # Maximum column width observed
    named_col_count: int = 0          # Columns with non-empty header string
    headers: List[str] = field(default_factory=list) # List of column header names
    columns: Dict[int, ColumnAuditMetrics] = field(default_factory=dict) # Keyed by 1-based col_idx
    candidate_pk_name: Optional[str] = None # Name of candidate primary key column
    candidate_pk_col_idx: Optional[int] = None # 1-based index of candidate PK
    pk_is_unique: bool = True         # True if candidate PK has zero duplicates and zero nulls
    pk_duplicate_count: int = 0       # Total duplicate PK instances (occurrences beyond first)
    pk_duplicate_samples: List[str] = field(default_factory=list) # Sample colliding keys
    full_duplicate_row_count: int = 0 # Rows where every cell exactly matches an earlier row
    total_cells: int = 0              # data_row_count * raw_col_count
    total_non_empty_cells: int = 0    # Sum of non_empty_count across all columns
    total_empty_cells: int = 0        # Sum of empty_count across all columns
    sheet_fill_rate: float = 0.0      # (total_non_empty_cells / total_cells) * 100
    total_urls_detected: int = 0      # Total URL instances found in sheet
    total_sentinels_detected: int = 0 # Total sentinel instances found in sheet
    domain_description: str = ""      # Architectural domain summary


@dataclass
class WorkbookAuditContext:
    """Global execution context and summary across all 21 sheets."""
    source_path: str                  # Path to raw source workbook
    file_size_bytes: int = 0          # Source file size on disk
    source_sha256: str = ""           # SHA-256 hash calculated before execution
    tool_version: str = "audit_workbook.py v1.0.0" # Static tool version
    sheet_count: int = 0              # Total sheets audited (must be 21)
    sheets: List[SheetAuditMetrics] = field(default_factory=list) # Ordered sheet audit objects
    total_rows_across_sheets: int = 0 # Sum of data_row_count
    total_cells_across_sheets: int = 0# Sum of total_cells
    total_non_empty_cells: int = 0    # Sum of non-empty cells
    total_empty_cells: int = 0        # Sum of empty cells
    overall_fill_rate: float = 0.0    # (total_non_empty / total_cells) * 100
    total_urls_across_sheets: int = 0 # Sum of URLs found
    total_sentinels_across_sheets: int = 0 # Sum of sentinels found
    immutability_verified: bool = False # Pre vs post SHA-256 match status
```

---

## 3. Detailed Metric Extraction Algorithms

### 3.1 Primary Key Uniqueness & Collision Detection

Primary key integrity is central to graph entity creation. The algorithm must:
1. Identify the candidate PK column for each sheet (either from the canonical schema directory or by scanning column headers ending in `_id` or `id`).
2. Track duplicate occurrences and distinguish distinct duplicate keys from total duplicate row instances.
3. Record deterministic samples of colliding keys.

```python
def analyze_primary_key_uniqueness(
    rows: List[tuple],
    pk_col_idx: int,
    pk_header_name: str
) -> tuple[bool, int, List[str]]:
    """
    Evaluates uniqueness of a candidate primary key column.
    
    Args:
        rows: Active data row tuples (excluding header row).
        pk_col_idx: 1-based index of candidate primary key column.
        pk_header_name: Name of PK column for logging.
        
    Returns:
        (is_unique, total_duplicate_instances, sample_colliding_keys)
    """
    seen_keys: Set[str] = set()
    colliding_keys: Set[str] = set()
    key_frequencies: Dict[str, int] = {}
    null_key_count = 0
    
    col_zero_idx = pk_col_idx - 1
    
    for row in rows:
        val = row[col_zero_idx] if col_zero_idx < len(row) else None
        
        # Check null / blank PK
        if val is None or (isinstance(val, str) and not val.strip()):
            null_key_count += 1
            continue
            
        key_str = str(val).strip()
        key_frequencies[key_str] = key_frequencies.get(key_str, 0) + 1
        
        if key_str in seen_keys:
            colliding_keys.add(key_str)
        else:
            seen_keys.add(key_str)
            
    # Calculate excess duplicate rows
    total_duplicates = sum(count - 1 for count in key_frequencies.values() if count > 1)
    
    # If null PKs exist, each null after the first is also considered a collision
    if null_key_count > 1:
        total_duplicates += (null_key_count - 1)
        colliding_keys.add("<NULL_OR_EMPTY_KEY>")
    elif null_key_count == 1:
        # A primary key column must not have nulls
        total_duplicates += 1
        colliding_keys.add("<NULL_KEY>")

    is_unique = (total_duplicates == 0 and null_key_count == 0)
    
    # Deterministic sorted sample (top 10 colliding keys)
    sample_colliding_keys = sorted(list(colliding_keys))[:10]
    
    return is_unique, total_duplicates, sample_colliding_keys
```

### 3.2 Full-Row Duplicate Detection

Full duplicate rows occur when two rows have identical cell values across all columns. To detect them efficiently without loading massive row trees:

```python
import hashlib

def normalize_cell_for_hashing(val: Any) -> str:
    """Normalizes cell values to consistent string representation for hashing."""
    if val is None:
        return ""
    if isinstance(val, bool):
        return "1" if val else "0"
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        # Prevent minute floating-point representation jitter
        return f"{val:.8g}"
    if isinstance(val, (datetime.datetime, datetime.date)):
        return val.isoformat()
    if isinstance(val, str):
        return val.strip()
    return str(val).strip()

def detect_full_duplicate_rows(rows: List[tuple]) -> int:
    """
    Computes total full duplicate rows in a sheet.
    Returns the count of rows that are identical duplicates of earlier rows.
    """
    seen_row_hashes: Set[str] = set()
    duplicate_row_count = 0
    
    for row in rows:
        normalized_elements = [normalize_cell_for_hashing(cell) for cell in row]
        row_signature = "||".join(normalized_elements)
        row_hash = hashlib.sha256(row_signature.encode("utf-8")).hexdigest()
        
        if row_hash in seen_row_hashes:
            duplicate_row_count += 1
        else:
            seen_row_hashes.add(row_hash)
            
    return duplicate_row_count
```

### 3.3 Active Data Row vs Trailing Blank Row Detection

Excel worksheets frequently report inflated dimensions because empty formatted cells or trailing deleted lines remain in the XML. The audit algorithm must:
- Treat a row as an active data row **only if** at least one cell in that row contains non-whitespace content.
- Count trailing blank rows separately in `empty_row_count` so fill rates are calculated strictly over active data rows.

```python
def is_row_empty(row: tuple) -> bool:
    """Returns True if every cell in the row is None or blank string."""
    for cell in row:
        if cell is not None:
            if isinstance(cell, str):
                if cell.strip():
                    return False
            else:
                return False
    return True

def separate_active_data_rows(raw_row_generator) -> tuple[Optional[tuple], List[tuple], int]:
    """
    Streams rows from openpyxl, extracts the header row, separates active
    data rows, and calculates trailing blank row counts.
    """
    header_row = None
    active_rows: List[tuple] = []
    empty_row_count = 0
    
    for row in raw_row_generator:
        # Find first non-empty row as header
        if header_row is None:
            if not is_row_empty(row):
                header_row = row
            continue
            
        if is_row_empty(row):
            empty_row_count += 1
        else:
            active_rows.append(row)
            
    return header_row, active_rows, empty_row_count
```

### 3.4 Empty vs Non-Empty Cell Counting & Fill Rate

For each column:
- `non_empty_count`: number of active data rows where `cell is not None and str(cell).strip() != ""`
- `empty_count`: number of active data rows where `cell is None or str(cell).strip() == ""`
- `total_cells`: `len(active_rows)`
- `fill_rate`: `(non_empty_count / total_cells) * 100.0 if total_cells > 0 else 0.0`
- Deterministic formatting: `f"{col.fill_rate:.2f}%"`

### 3.5 URL Pattern Matching & Leakage Detection Engine

Raw URLs must be detected, counted, and flagged for migration to `provenance.csv`.

#### Regex Specification
```python
import re

URL_PATTERN = re.compile(
    r'(https?://[^\s"\'<>]+|www\.[^\s"\'<>]+|(?:[a-zA-Z0-9-]+\.)+(?:com|eu|org|net|de|co\.uk|jp)(?:/[^\s"\'<>]*)?)',
    re.IGNORECASE
)
```

#### Prevention of False Positives
The regex must NOT trigger on:
- Model numbers containing hyphens and periods (e.g., `ZX250-7`, `ZX330LC-5G`)
- Decimal numbers (e.g., `32.5`)
- Component codes (e.g., `CAT-EXC`)

The regex above requires either `http://`, `https://`, `www.`, or a recognized top-level domain (`.com`, `.eu`, `.org`, `.net`, `.de`, `.co.uk`, `.jp`) with preceding alphanumeric domain tokens.

```python
def check_url_leakage(val: Any) -> tuple[bool, List[str]]:
    """Detects whether a cell contains one or more URL strings."""
    if not isinstance(val, str):
        return False, []
    matches = URL_PATTERN.findall(val)
    return bool(matches), matches
```

### 3.6 Sentinel Value Detection

Sentinel values represent missing, undisclosed, or legacy placeholder values. They must be counted and flagged so that downstream normalization can sanitize them into empty strings (`""`).

#### Canonical Sentinel Vocabulary
```python
SENTINEL_EXACT_SET = {
    "NOT PUBLICLY STATED",
    "NOT STATED",
    "NOT APPLICABLE",
    "N/A",
    "NA",
    "N / A",
    "-",
    "--",
    "---",
    "TBD",
    "TBA",
    "UNKNOWN",
    "NONE",
    "NULL",
    "#N/A",
    "#VALUE!",
    "#REF!",
    "#NAME?",
    "?",
}

def detect_sentinel_value(val: Any) -> tuple[bool, Optional[str]]:
    """
    Checks if a cell value matches known sentinel patterns.
    Returns (is_sentinel, canonical_sentinel_name).
    """
    if not isinstance(val, str):
        return False, None
        
    cleaned = val.strip().upper()
    
    if cleaned in SENTINEL_EXACT_SET:
        return True, cleaned
        
    if cleaned.startswith("NOT PUBLICLY STATED"):
        return True, "NOT PUBLICLY STATED"
        
    return False, None
```

### 3.7 Inferred Python Data Types

When reading cells via openpyxl `data_only=True`, cell values take on native Python types. Note that Python's `bool` is a subclass of `int` (`isinstance(True, int) == True`). Therefore, the type-checking order is critical:

```python
import datetime

def infer_cell_type(val: Any) -> str:
    """Infers the exact Python primitive type name for a cell value."""
    if val is None:
        return "NoneType"
    if isinstance(val, bool): # Must check bool before int!
        return "bool"
    if isinstance(val, int):
        return "int"
    if isinstance(val, float):
        return "float"
    if isinstance(val, (datetime.datetime, datetime.date, datetime.time)):
        return "datetime"
    if isinstance(val, str):
        return "str"
    return type(val).__name__
```

### 3.8 Column Utility Classification Taxonomy

Every column across all 21 sheets must be categorized into one of five functional classifications:

| Classification | Meaning | Examples |
|---|---|---|
| `TECHNICAL_ENTITY_ATTRIBUTE` | Genuine physical, engineering, or operational property of a node. | `operating_weight_kg`, `rated_power_kw`, `bucket_capacity_m3`, `status` |
| `GRAPH_RELATIONSHIP_POINTER` | Foreign key or node reference pointer used to establish graph edges. | `machine_id`, `category_id`, `part_id`, `parent_category_id`, `service_id` |
| `PROVENANCE_METADATA` | Source citation, extraction date, confidence rating, or URL store. | `source_url`, `source_name`, `extracted_date`, `confidence`, `evidence_type` |
| `CONTROLLED_VOCAB_FIELD` | Domain enum requiring normalization against a controlled dictionary. | `record_class`, `fitment_evidence`, `classification`, `location_capabilities` |
| `NOISE_TO_REMOVE` | Ephemeral website merchandising, search ranking, or cart UI noise. | `ui_search_rank`, `featured_badge`, `display_priority`, `ui_order`, `marketing_copy` |

#### Heuristic Classification Decision Tree
```python
def classify_column_utility(header: str, sample_types: Set[str], url_count: int, total_rows: int) -> tuple[str, str]:
    """
    Classifies a column into one of the 5 utility categories with rationale.
    """
    h_lower = header.lower().strip()
    
    # 1. Noise check
    noise_keywords = ["ui_", "rank", "badge", "featured", "display_priority", "order", "shopping_cart", "marketing_copy"]
    if any(kw in h_lower for kw in noise_keywords):
        return "NOISE_TO_REMOVE", "UI merchandising or search ranking field to strip"
        
    # 2. Provenance check
    prov_keywords = ["url", "source", "evidence", "provenance", "extracted", "citation"]
    if any(kw in h_lower for kw in prov_keywords) or (url_count > 0 and url_count >= total_rows * 0.5):
        return "PROVENANCE_METADATA", "Citation, web URL, or evidence metadata for provenance store"
        
    # 3. Graph Relationship Pointer check
    fk_suffixes = ["_id", "id", "parent_category", "mapping_id"]
    if any(h_lower.endswith(suf) or h_lower == suf for suf in fk_suffixes):
        return "GRAPH_RELATIONSHIP_POINTER", "Primary key or foreign key reference for graph relationships"
        
    # 4. Controlled Vocabulary check
    vocab_keywords = ["class", "tier", "level", "evidence", "classification", "type", "category"]
    if any(kw in h_lower for kw in vocab_keywords):
        return "CONTROLLED_VOCAB_FIELD", "Categorical field requiring controlled vocabulary validation"
        
    # 5. Default: Technical Attribute
    return "TECHNICAL_ENTITY_ATTRIBUTE", "Core technical or domain property for graph node"
```

---

## 4. Openpyxl Memory Safety & Stream Processing

### 4.1 `read_only=True, data_only=True` Architecture

`openpyxl.load_workbook(filename, read_only=True, data_only=True)` provides the following safeguards:
- `read_only=True`: Uses an iterative streaming XML parser (`cElementTree.iterparse`). Rows are read on demand from the underlying zip stream and immediately discarded after processing. This guarantees negligible RAM usage even for multi-sheet workbooks.
- `data_only=True`: Evaluates formula cells to their cached computed results (e.g. string or numeric results), suppressing raw formula strings (e.g. `=CONCATENATE(...)`).

### 4.2 Handling Generator Semantics & Dimension Hazards
In openpyxl read-only mode:
- `ws.iter_rows(values_only=True)` yields tuples of raw cell values directly, avoiding the overhead of `ReadOnlyCell` wrapper objects.
- **Dimension Hazard**: `ws.max_row` and `ws.max_column` in read-only mode are often `None` or inaccurate because Excel does not mandate an XML dimension header.
  - **Invariant**: The audit script must **never** rely on `ws.max_row` or `ws.max_column`.
  - Dimensions must be computed on-the-fly during row streaming.

### 4.3 Safe Handling of Merged Cells
- In `read_only=True`, openpyxl does **not** populate `ws.merged_cells` (to save memory and avoid non-streaming lookaheads).
- Only the top-left cell of a merged block contains the cell value; adjacent merged cells stream as `None`.
- **Mitigation for Header Row**:
  - If a cell in the header row is `None` (due to merged headers or blank columns), the audit algorithm must assign a deterministic fallback: `f"UNNAMED_COL_{col_idx}"`.
  - It must never throw an `AttributeError` or crash when processing `None` headers.

### 4.4 Date and Datetime Object Handling
- Excel date cells are parsed by openpyxl as `datetime.datetime`, `datetime.date`, or `datetime.time`.
- These objects cannot be directly compared with string values in Python sorting operations (`TypeError`).
- **Mitigation**:
  - When storing sample values or formatting for markdown: always convert to ISO-8601 string: `val.isoformat()` or `val.strftime("%Y-%m-%d")`.
  - For hashing, use ISO-8601 string representation.

### 4.5 Guaranteed Resource Cleanup
In `read_only=True` mode, openpyxl holds open file descriptors on the underlying `.xlsx` zip archive. Failure to close the workbook can result in Windows file locking bugs or resource leaks.
- **Pattern**:
```python
wb = None
try:
    wb = openpyxl.load_workbook(source_path, read_only=True, data_only=True)
    # Perform streaming audit
finally:
    if wb is not None:
        wb.close()
```

---

## 5. 100% Byte-Level Determinism Controls

To guarantee that running `audit_workbook.py` twice produces **bit-for-bit identical markdown output**:

### 5.1 Static Report Header (Zero Volatile Timestamps)
Dynamic values such as `datetime.now()`, `time.time()`, or process runtimes must **never** be written to `neo4j/reports/workbook_audit.md`.

Instead, the report header must use the static cryptographic SHA-256 hash of the input file:

```markdown
# HCME After-Sales Data Foundation: Source Workbook Audit (21 Sheets)

- **Source File**: `HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx`
- **Source SHA-256**: `[COMPUTED_64_HEX_HASH]`
- **Source File Size**: `815104 bytes`
- **Audit Tool**: `audit_workbook.py v1.0.0`
- **Integrity Status**: `VERIFIED_UNTOUCHED`
- **Total Worksheets Audited**: `21`
```

### 5.2 Deterministic Dictionary and Set Iteration
- Iteration over Python `set` objects is non-deterministic across Python processes due to hash seed randomization (`PYTHONHASHSEED`).
- **Invariant**: Any collection derived from a `set` (e.g. data types, sample values, duplicate key samples) must be explicitly sorted before string formatting:
  ```python
  types_str = ", ".join(sorted(list(col.inferred_types)))
  duplicates_str = ", ".join(sorted(col.sample_values)[:5])
  ```
- Dictionaries representing columns must be indexed and iterated strictly by 1-based column integer index (`1..col_count`).

### 5.3 Fixed Float Precision
Floating point numbers can display trailing precision differences across platforms.
- Every percentage must use fixed formatting: `f"{value:.2f}%"`.
- Every float metric must use explicit formatting: `f"{value:.2f}"` or integer conversion where applicable.

### 5.4 Cross-Platform Line Endings and Encoding
Windows platforms default to `\r\n` (CRLF), whereas Linux/macOS use `\n` (LF).
- **Invariant**: When opening the markdown report for writing, explicitly enforce `newline='\n'` and `encoding='utf-8'`:
  ```python
  with open(output_path, "w", encoding="utf-8", newline="\n") as f:
      f.write(markdown_content)
  ```

---

## 6. Source Immutability Verification Protocol

To satisfy Critical Constraint 1 and Acceptance Criteria R1/R5, `audit_workbook.py` must enforce strict pre- and post-read verification:

```python
import hashlib
import os
from pathlib import Path


class SourceImmutabilityError(Exception):
    """Raised when the source workbook is modified or corrupted during execution."""
    pass


def calculate_sha256(file_path: Path) -> str:
    """Calculates SHA-256 hash of a file using chunked binary reading."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def audit_with_immutability_verification(source_path: Path, output_path: Path):
    """
    Executes source audit wrapped with strict pre- and post-read immutability checks.
    """
    if not source_path.exists():
        sys.exit(2) # Exit code 2: Source missing
        
    # 1. Pre-execution baseline capture
    stat_before = os.stat(source_path)
    sha_before = calculate_sha256(source_path)
    mtime_before_ns = stat_before.st_mtime_ns
    
    # 2. Execute read-only streaming audit
    audit_context = execute_audit(source_path, sha_before, stat_before.st_size)
    
    # 3. Post-execution verification
    stat_after = os.stat(source_path)
    sha_after = calculate_sha256(source_path)
    mtime_after_ns = stat_after.st_mtime_ns
    
    if sha_before != sha_after:
        raise SourceImmutabilityError(
            f"FATAL: Source workbook SHA-256 hash modified! Before: {sha_before}, After: {sha_after}"
        )
        
    if mtime_before_ns != mtime_after_ns:
        raise SourceImmutabilityError(
            f"FATAL: Source workbook modification timestamp altered! Before: {mtime_before_ns}, After: {mtime_after_ns}"
        )
        
    audit_context.immutability_verified = True
    
    # 4. Deterministic Markdown serialization
    render_markdown_report(audit_context, output_path)
```

### Process Exit Code Specifications
- `0`: Success. All 21 sheets parsed, metrics calculated, immutability verified, report written.
- `1`: Invalid CLI arguments or syntax error.
- `2`: Source workbook file missing or unreadable.
- `3`: Source immutability violation (hash or mtime changed).

---

## 7. Canonical Catalog of All 21 Source Sheets for Audit Execution

The table below provides the canonical reference baseline for `audit_workbook.py` when validating worksheet names, primary keys, and domain scope:

| Sheet # | Canonical Sheet Name | Expected Domain | Primary Key Column | Expected Target in Clean Model |
|:---:|---|---|---|---|
| **00** | `00_README` | Data dictionary & sheet inventory | `sheet_name` / `sheet_index` | Sheet `00_README` (Metadata) |
| **01** | `01_CATEGORIES` | Machine taxonomic hierarchy | `category_id` | `categories.csv` & Sheet `01_CATEGORIES` |
| **02** | `02_MACHINE_MASTER` | Machine catalogue records | `machine_id` | `machines.csv` & Sheet `02_MACHINES` |
| **03** | `03_MACHINE_SPECIFICATIONS` | Engineering specifications | `spec_id` / `machine_id` | `specifications.csv` & Sheet `03_SPECIFICATIONS` |
| **04** | `04_MACHINE_APPLICATIONS` | Machine-application mappings | `mapping_id` | `applications.csv` & Sheet `04_APPLICATIONS` |
| **05** | `05_ATTACHMENTS` | OEM attachments catalogue | `attachment_id` | `attachments.csv` & Sheet `05_ATTACHMENTS` |
| **06** | `06_PART_MASTER` | Orderable parts & product families | `part_id` | `parts.csv` & Sheet `06_PARTS` |
| **07** | `07_MACHINE_PART_FITMENT` | Machine-part fitment matrix | `fitment_id` | `machine_part_fitment.csv` & Sheet `07` |
| **08** | `08_SERVICE_CAPABILITIES` | Service programs & locations | `service_id` | `services.csv` & Sheet `08_SERVICES` |
| **09** | `09_MACHINE_SERVICE_MATRIX` | Service eligibility matrix | `mapping_id` | `machine_service.csv` & Sheet `09_MACHINE_SERVICE` |
| **10** | `10_MAINTENANCE_SCHEDULE` | Periodic maintenance intervals | `maintenance_id` | `maintenance.csv` & Sheet `10_MAINTENANCE` |
| **11** | `11_SERVICE_PART_REQUIREMENTS` | Maintenance task BOM | `requirement_id` | `service_part_requirements.csv` & Sheet `11` |
| **12** | `12_MACHINE_DIGITAL_SERVICES` | ConSite telematics matrix | `digital_service_id` | `digital_services.csv` & Sheet `12_DIGITAL_SERVICES` |
| **13** | `13_AFTER_SALES_RELATIONSHIPS`| Master relationship ledger | `rel_id` | `relationships.csv` & Sheet `13_RELATIONSHIPS` |
| **14** | `14_SOURCE_PROVENANCE` | External citations & URLs | `provenance_id` | `provenance.csv` & Sheet `14_PROVENANCE` |
| **15** | `15_DEALER_NETWORK` | Dealer workshops & locations | `dealer_id` | Consolidated to `08_SERVICES` |
| **16** | `16_WARRANTY_PROGRAMS` | Warranty tiers & coverage | `program_id` | Consolidated to `08_SERVICES` / `13_RELATIONSHIPS` |
| **17** | `17_TELEMATICS_METRICS` | ConSite sensors & alerts | `metric_id` | Consolidated to `12_DIGITAL_SERVICES` |
| **18** | `18_REMAN_PARTS` | Reman components exchange | `reman_id` | Consolidated to `06_PARTS` (`PRODUCT_LINE_PART_FAMILY`) |
| **19** | `19_CONSUMABLES_LUBRICANTS` | Genuine oils & lubricants | `consumable_id` | Consolidated to `06_PARTS` |
| **20** | `20_OPERATOR_MANUALS` | Manuals & training guides | `doc_id` | Consolidated to `14_PROVENANCE` / `00_README` |

---

## 8. Reference Implementation Architecture (Code Blueprint)

The following modular blueprint shows how the data structures, algorithms, openpyxl stream processing, and determinism controls assemble into a complete, testable module:

```python
"""
Core computational audit engine for audit_workbook.py
Designed by explorer_m1_2.
"""
import hashlib
import os
import re
import sys
import datetime
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional, Any
from collections import Counter
import openpyxl
from openpyxl.utils import get_column_letter


# [Data Structures defined in Section 2 above]


class WorkbookAuditScanner:
    """Executes non-destructive, deterministic audit of 21-sheet workbook."""

    def __init__(self, source_path: Path, tool_version: str = "audit_workbook.py v1.0.0"):
        self.source_path = source_path
        self.tool_version = tool_version

    def run(self) -> WorkbookAuditContext:
        """Main audit runner with strict immutability checks."""
        if not self.source_path.exists():
            print(f"ERROR: Source file not found at {self.source_path}", file=sys.stderr)
            sys.exit(2)

        stat_before = os.stat(self.source_path)
        sha_before = calculate_sha256(self.source_path)
        mtime_before = stat_before.st_mtime_ns

        context = WorkbookAuditContext(
            source_path=str(self.source_path),
            file_size_bytes=stat_before.st_size,
            source_sha256=sha_before,
            tool_version=self.tool_version,
        )

        wb = None
        try:
            # Memory-safe streaming load
            wb = openpyxl.load_workbook(self.source_path, read_only=True, data_only=True)
            context.sheet_count = len(wb.sheetnames)

            for idx, sheet_name in enumerate(wb.sheetnames, start=1):
                ws = wb[sheet_name]
                sheet_metrics = self._audit_single_sheet(ws, idx, sheet_name)
                context.sheets.append(sheet_metrics)

        finally:
            if wb is not None:
                wb.close()

        # Post-read verification
        stat_after = os.stat(self.source_path)
        sha_after = calculate_sha256(self.source_path)
        mtime_after = stat_after.st_mtime_ns

        if sha_before != sha_after or mtime_before != mtime_after:
            print("CRITICAL: Source workbook immutability violated!", file=sys.stderr)
            sys.exit(3)

        context.immutability_verified = True
        self._aggregate_summary_metrics(context)
        return context

    def _audit_single_sheet(self, ws, sheet_index: int, sheet_name: str) -> SheetAuditMetrics:
        """Audits a single sheet using row streaming."""
        metrics = SheetAuditMetrics(sheet_index=sheet_index, sheet_name=sheet_name)
        
        # Stream rows
        row_gen = ws.iter_rows(values_only=True)
        header_tuple, active_rows, empty_row_count = separate_active_data_rows(row_gen)
        
        metrics.data_row_count = len(active_rows)
        metrics.empty_row_count = empty_row_count
        metrics.raw_row_count = (1 if header_tuple else 0) + metrics.data_row_count + empty_row_count
        
        if not header_tuple:
            # Entirely empty sheet
            return metrics

        # Determine column width
        num_cols = len(header_tuple)
        metrics.raw_col_count = num_cols
        
        # Initialize column metrics
        for col_idx in range(1, num_cols + 1):
            raw_h = header_tuple[col_idx - 1]
            h_str = str(raw_h).strip() if raw_h is not None else f"UNNAMED_COL_{col_idx}"
            if h_str and not h_str.startswith("UNNAMED_COL_"):
                metrics.named_col_count += 1
            metrics.headers.append(h_str)
            
            metrics.columns[col_idx] = ColumnAuditMetrics(
                col_idx=col_idx,
                col_letter=get_column_letter(col_idx),
                header=h_str,
                raw_header=str(raw_h) if raw_h is not None else None,
                total_cells=metrics.data_row_count
            )

        # Candidate PK identification
        candidate_pk = CANONICAL_SHEET_PK_MAP.get(sheet_name)
        if candidate_pk and candidate_pk in metrics.headers:
            metrics.candidate_pk_name = candidate_pk
            metrics.candidate_pk_col_idx = metrics.headers.index(candidate_pk) + 1
        elif num_cols > 0:
            # Fallback heuristic: first column ending with _id or id
            for col_idx in range(1, num_cols + 1):
                h = metrics.headers[col_idx - 1].lower()
                if h.endswith("_id") or h == "id":
                    metrics.candidate_pk_name = metrics.headers[col_idx - 1]
                    metrics.candidate_pk_col_idx = col_idx
                    break

        # Process active data rows
        distinct_col_values: Dict[int, Set[str]] = {c: set() for c in range(1, num_cols + 1)}

        for row in active_rows:
            for col_idx in range(1, num_cols + 1):
                col_m = metrics.columns[col_idx]
                val = row[col_idx - 1] if col_idx - 1 < len(row) else None
                
                # Inferred type
                val_type = infer_cell_type(val)
                col_m.inferred_types.add(val_type)
                
                # Empty vs Non-Empty
                if val is None or (isinstance(val, str) and not val.strip()):
                    col_m.empty_count += 1
                else:
                    col_m.non_empty_count += 1
                    val_str = str(val).strip()
                    distinct_col_values[col_idx].add(val_str)
                    
                    # URL check
                    has_url, matches = check_url_leakage(val)
                    if has_url:
                        col_m.url_count += 1
                        metrics.total_urls_detected += len(matches)
                        
                    # Sentinel check
                    is_sentinel, sentinel_name = detect_sentinel_value(val)
                    if is_sentinel:
                        col_m.sentinel_count += 1
                        col_m.sentinel_breakdown[sentinel_name] += 1
                        metrics.total_sentinels_detected += 1
                        
                    # Whitespace / formatting check
                    if isinstance(val, str):
                        if "\u00a0" in val or val != val.strip() or "\n" in val:
                            col_m.whitespace_issues_count += 1

        # Post-process columns
        for col_idx in range(1, num_cols + 1):
            col_m = metrics.columns[col_idx]
            col_m.cardinality = len(distinct_col_values[col_idx])
            col_m.fill_rate = (col_m.non_empty_count / col_m.total_cells * 100.0) if col_m.total_cells > 0 else 0.0
            # Deterministic sorted sample
            col_m.sample_values = sorted(list(distinct_col_values[col_idx]))[:5]
            # Classification
            cat, rationale = classify_column_utility(
                col_m.header, col_m.inferred_types, col_m.url_count, col_m.total_cells
            )
            col_m.utility_classification = cat
            col_m.classification_rationale = rationale

        # Full duplicate rows
        metrics.full_duplicate_row_count = detect_full_duplicate_rows(active_rows)

        # Primary key uniqueness
        if metrics.candidate_pk_col_idx:
            is_uniq, dups, samples = analyze_primary_key_uniqueness(
                active_rows, metrics.candidate_pk_col_idx, metrics.candidate_pk_name or ""
            )
            metrics.pk_is_unique = is_uniq
            metrics.pk_duplicate_count = dups
            metrics.pk_duplicate_samples = samples

        # Sheet fill rate
        metrics.total_cells = metrics.data_row_count * metrics.raw_col_count
        metrics.total_non_empty_cells = sum(c.non_empty_count for c in metrics.columns.values())
        metrics.total_empty_cells = sum(c.empty_count for c in metrics.columns.values())
        metrics.sheet_fill_rate = (
            (metrics.total_non_empty_cells / metrics.total_cells * 100.0) if metrics.total_cells > 0 else 0.0
        )
        return metrics

    def _aggregate_summary_metrics(self, context: WorkbookAuditContext):
        """Computes rollup metrics across all worksheets."""
        for sm in context.sheets:
            context.total_rows_across_sheets += sm.data_row_count
            context.total_cells_across_sheets += sm.total_cells
            context.total_non_empty_cells += sm.total_non_empty_cells
            context.total_empty_cells += sm.total_empty_cells
            context.total_urls_across_sheets += sm.total_urls_detected
            context.total_sentinels_across_sheets += sm.total_sentinels_detected
            
        if context.total_cells_across_sheets > 0:
            context.overall_fill_rate = (
                context.total_non_empty_cells / context.total_cells_across_sheets * 100.0
            )


CANONICAL_SHEET_PK_MAP = {
    "00_README": "sheet_name",
    "01_CATEGORIES": "category_id",
    "02_MACHINE_MASTER": "machine_id",
    "03_MACHINE_SPECIFICATIONS": "spec_id",
    "04_MACHINE_APPLICATIONS": "mapping_id",
    "05_ATTACHMENTS": "attachment_id",
    "06_PART_MASTER": "part_id",
    "07_MACHINE_PART_FITMENT": "fitment_id",
    "08_SERVICE_CAPABILITIES": "service_id",
    "09_MACHINE_SERVICE_MATRIX": "mapping_id",
    "10_MAINTENANCE_SCHEDULE": "maintenance_id",
    "11_SERVICE_PART_REQUIREMENTS": "requirement_id",
    "12_MACHINE_DIGITAL_SERVICES": "digital_service_id",
    "13_AFTER_SALES_RELATIONSHIPS": "rel_id",
    "14_SOURCE_PROVENANCE": "provenance_id",
    "15_DEALER_NETWORK": "dealer_id",
    "16_WARRANTY_PROGRAMS": "program_id",
    "17_TELEMATICS_METRICS": "metric_id",
    "18_REMAN_PARTS": "reman_id",
    "19_CONSUMABLES_LUBRICANTS": "consumable_id",
    "20_OPERATOR_MANUALS": "doc_id",
}
```

---

## 9. Verification & Acceptance Testing Guidelines

To verify that `audit_workbook.py` correctly implements this specification:

1. **Source Immutability Test**:
   - Record SHA-256 and `st_mtime` before running `audit_workbook.py`.
   - Execute `audit_workbook.py`.
   - Assert post-execution SHA-256 and `st_mtime` match the baseline exactly.
2. **Double-Run Byte Determinism Test**:
   - Run `python audit_workbook.py --output /tmp/run1.md`
   - Run `python audit_workbook.py --output /tmp/run2.md`
   - Assert `hashlib.sha256(open('/tmp/run1.md', 'rb').read()).hexdigest() == hashlib.sha256(open('/tmp/run2.md', 'rb').read()).hexdigest()`
3. **21-Sheet Audit Completeness**:
   - Verify that all 21 sheets (`00_README` through `20_OPERATOR_MANUALS`) are present in `workbook_audit.md`.
   - Verify exact metrics: total rows, active data rows, column count, fill rate, PK uniqueness, URL count, and sentinel counts.
4. **Strict Neo4j Isolation Check**:
   - Assert zero imports of `neo4j` or `py2neo`.
   - Assert zero socket connections to port 7687 or 7474.
