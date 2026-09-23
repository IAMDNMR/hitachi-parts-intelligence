# Source Workbook Audit Report

Source: `C:\Users\iamdn\Downloads\HITACHI_OEM_AfterSales_Parts_Services_DataFoundation.xlsx`
SHA-256: `53bd4845233a7330a2d819d1fdc849dfb5d67c542101eceaf5ef3d9bd798d338`
Sheets audited: 21

Row/column layout verified directly from the file: row 1 is a free-text note, row 2 is blank, row 3 is the real header row, data starts row 4. Every sheet name, header, and count below was read from the file — none of it is assumed or carried over from any other report.

## 1. Sheet Rollup

| # | Sheet | Rows | Cols | Duplicate rows | ID column | Duplicate IDs |
|---|-------|------|------|------|------|------|
| 0 | 00_README | 70 | 2 | 0 | — | 0 |
| 1 | 01_MACHINE_CATEGORIES | 17 | 14 | 0 | Category ID | 0 |
| 2 | 02_MACHINE_MASTER | 77 | 36 | 0 | Machine ID | 0 |
| 3 | 03_MACHINE_SPECIFICATIONS | 1635 | 14 | 0 | Spec ID | 0 |
| 4 | 04_MACHINE_APPLICATIONS | 328 | 12 | 0 | junction — no per-row ID | 0 |
| 5 | 05_ATTACHMENTS | 17 | 20 | 0 | Attachment ID | 0 |
| 6 | 06_PART_MASTER | 43 | 21 | 0 | Part ID | 0 |
| 7 | 07_MACHINE_PART_FITMENT | 944 | 17 | 0 | Fitment ID | 0 |
| 8 | 08_SERVICE_CAPABILITIES | 22 | 18 | 0 | Service ID | 0 |
| 9 | 09_MACHINE_SERVICE_MATRIX | 1694 | 20 | 0 | junction — no per-row ID | 0 |
| 10 | 10_MAINTENANCE_SCHEDULE | 10 | 20 | 0 | Maintenance ID | 0 |
| 11 | 11_SERVICE_PART_REQUIREMENTS | 11 | 17 | 0 | Requirement ID | 0 |
| 12 | 12_MACHINE_DIGITAL_SERVICES | 616 | 20 | 0 | junction — no per-row ID | 0 |
| 13 | 13_AFTER_SALES_RELATIONSHIPS | 3283 | 14 | 0 | Relationship ID | 0 |
| 14 | 14_SOURCE_REGISTER | 47 | 10 | 0 | — | 0 |
| 15 | 15_DATA_QUALITY | 40 | 9 | 0 | junction — no per-row ID | 0 |
| 16 | 16_CATEGORY_COMPARISON | 12 | 16 | 0 | Category ID | 0 |
| 17 | 17_COMMON_VS_SPECIFIC | 34 | 8 | 0 | Analysis ID | 0 |
| 18 | 18_DATA_DICTIONARY | 68 | 10 | 0 | — | 0 |
| 19 | 19_RELATIONSHIP_SCHEMA | 18 | 8 | 0 | Schema ID | 0 |
| 20 | 20_COMPLETENESS_CHECK | 33 | 6 | 0 | Check ID | 0 |

## 2. Per-Sheet Detail

### 00_README

Rows: 70 · Columns: 2 · Duplicate rows: 0 · ID column: — (duplicates: 0)

| Column | Non-empty | Empty | Unique | Flags |
|---|---|---|---|---|
| Purpose | 70 | 0 | 70 |  |
| Structured, fully traceable source data from which the application’s Machine, Parts, Fitment, Service and After-Sales models can be designed and populated. This is a master/reference data foundation - it deliberately contains NO operational Service Jobs, Technicians or Service Locations. | 62 | 8 | 62 | SOURCE/EVIDENCE, URL |

### 01_MACHINE_CATEGORIES

Rows: 17 · Columns: 14 · Duplicate rows: 0 · ID column: Category ID (duplicates: 0)

| Column | Non-empty | Empty | Unique | Flags |
|---|---|---|---|---|
| Category ID | 17 | 0 | 17 |  |
| Parent Category | 17 | 0 | 4 |  |
| Category Name | 17 | 0 | 17 |  |
| Official Category Name | 17 | 0 | 17 | SOURCE/EVIDENCE |
| Category Description | 17 | 0 | 17 |  |
| Product Type | 17 | 0 | 7 |  |
| Machine Configuration | 15 | 2 | 15 |  |
| On-road / Off-road | 16 | 1 | 4 |  |
| Primary Application | 17 | 0 | 17 |  |
| Official URL | 17 | 0 | 17 | SOURCE/EVIDENCE, URL |
| Source | 17 | 0 | 1 | SOURCE/EVIDENCE |
| Source ID | 17 | 0 | 11 | SOURCE/EVIDENCE |
| Source Date | 17 | 0 | 1 | SOURCE/EVIDENCE |
| Notes | 17 | 0 | 2 | NOTES/RESEARCH, SOURCE/EVIDENCE |

### 02_MACHINE_MASTER

Rows: 77 · Columns: 36 · Duplicate rows: 0 · ID column: Machine ID (duplicates: 0)

| Column | Non-empty | Empty | Unique | Flags |
|---|---|---|---|---|
| Machine ID | 77 | 0 | 77 |  |
| Manufacturer | 77 | 0 | 1 |  |
| Brand | 77 | 0 | 1 |  |
| Machine Category | 77 | 0 | 3 |  |
| Machine Subcategory | 77 | 0 | 12 |  |
| Category ID | 77 | 0 | 12 |  |
| Product Family | 77 | 0 | 5 |  |
| Model | 77 | 0 | 72 |  |
| Models Covered | 77 | 0 | 72 |  |
| Model Count | 77 | 0 | 2 |  |
| Generation / Series | 73 | 4 | 4 |  |
| Machine Type | 77 | 0 | 3 |  |
| Configuration | 77 | 0 | 13 |  |
| Power Source | 77 | 0 | 2 | SOURCE/EVIDENCE |
| Official Product Name | 77 | 0 | 77 | SOURCE/EVIDENCE |
| Official Product URL | 77 | 0 | 77 | SOURCE/EVIDENCE, URL |
| Available In | 70 | 7 | 2 |  |
| Engine / Motor Rated Power | 73 | 4 | 50 |  |
| Operating Weight (as published) | 77 | 0 | 75 |  |
| Operating Weight (kg, normalised) | 77 | 0 | 72 |  |
| Bucket Capacity (as published) | 56 | 21 | 44 |  |
| Battery Capacity | 3 | 74 | 3 |  |
| Nominal Payload | 3 | 74 | 3 |  |
| Max. Digging Depth | 60 | 17 | 56 |  |
| Max. Digging Reach | 41 | 36 | 39 |  |
| Overall Width | 23 | 54 | 15 |  |
| Overall Height of Cab | 32 | 45 | 22 |  |
| Fuel Tank Capacity | 4 | 73 | 4 |  |
| Published Spec Row Count | 77 | 0 | 26 |  |
| Published Spec Groups | 77 | 0 | 17 |  |
| Official Overview Text | 77 | 0 | 68 | SOURCE/EVIDENCE |
| Brochure PDF | 77 | 0 | 65 | URL |
| Data Class | 77 | 0 | 1 | SOURCE/EVIDENCE |
| Source ID | 77 | 0 | 1 | SOURCE/EVIDENCE |
| Source Date | 77 | 0 | 1 | SOURCE/EVIDENCE |
| Notes | 77 | 0 | 1 | NOTES/RESEARCH, SOURCE/EVIDENCE |

### 03_MACHINE_SPECIFICATIONS

Rows: 1635 · Columns: 14 · Duplicate rows: 0 · ID column: Spec ID (duplicates: 0)

| Column | Non-empty | Empty | Unique | Flags |
|---|---|---|---|---|
| Spec ID | 1635 | 0 | 1635 |  |
| Machine ID | 1635 | 0 | 77 |  |
| Model | 1635 | 0 | 72 |  |
| Machine Subcategory | 1635 | 0 | 12 |  |
| Specification Group | 1635 | 0 | 24 |  |
| Specification Name | 1635 | 0 | 124 |  |
| Specification Value | 1635 | 0 | 1052 |  |
| Unit | 1046 | 589 | 17 |  |
| Normalised Value | 480 | 1155 | 276 |  |
| Data Class | 1635 | 0 | 1 | SOURCE/EVIDENCE |
| Source ID | 1635 | 0 | 1 | SOURCE/EVIDENCE |
| Official URL | 1635 | 0 | 77 | SOURCE/EVIDENCE, URL |
| Source Date | 1635 | 0 | 1 | SOURCE/EVIDENCE |
| Notes | 1635 | 0 | 1 | NOTES/RESEARCH, SOURCE/EVIDENCE |

### 04_MACHINE_APPLICATIONS

Rows: 328 · Columns: 12 · Duplicate rows: 0 · ID column: junction table — no per-row ID column (duplicates: 0)

| Column | Non-empty | Empty | Unique | Flags |
|---|---|---|---|---|
| Machine ID | 328 | 0 | 77 |  |
| Model | 328 | 0 | 72 |  |
| Machine Subcategory | 328 | 0 | 12 |  |
| Application | 328 | 0 | 29 |  |
| Application Type | 328 | 0 | 2 |  |
| Official Description | 328 | 0 | 12 | SOURCE/EVIDENCE |
| Data Class | 328 | 0 | 1 | SOURCE/EVIDENCE |
| Source ID | 328 | 0 | 7 | SOURCE/EVIDENCE |
| Source URL | 328 | 0 | 7 | SOURCE/EVIDENCE, URL |
| Confidence | 328 | 0 | 1 | SOURCE/EVIDENCE |
| Source Date | 328 | 0 | 1 | SOURCE/EVIDENCE |
| Notes | 328 | 0 | 1 | NOTES/RESEARCH, SOURCE/EVIDENCE |

### 05_ATTACHMENTS

Rows: 17 · Columns: 20 · Duplicate rows: 0 · ID column: Attachment ID (duplicates: 0)

| Column | Non-empty | Empty | Unique | Flags |
|---|---|---|---|---|
| Attachment ID | 17 | 0 | 17 |  |
| Attachment Name | 17 | 0 | 17 |  |
| Attachment Type | 17 | 0 | 8 |  |
| Attachment Category | 17 | 0 | 5 |  |
| Machine ID | 17 | 0 | 1 |  |
| Compatible Machine Model | 7 | 10 | 7 |  |
| Compatible Machine Category | 17 | 0 | 15 |  |
| Mounting / Coupling Type | 10 | 7 | 6 |  |
| Hydraulic Requirement | 14 | 3 | 7 |  |
| Weight | 0 | 17 | 0 |  |
| Dimensions | 0 | 17 | 0 |  |
| Capacity | 7 | 10 | 7 |  |
| Purpose / Application | 17 | 0 | 17 |  |
| Detachable / Fixed | 17 | 0 | 5 |  |
| Official URL | 17 | 0 | 7 | SOURCE/EVIDENCE, URL |
| Data Class | 17 | 0 | 1 | SOURCE/EVIDENCE |
| Source ID | 17 | 0 | 7 | SOURCE/EVIDENCE |
| Confidence | 17 | 0 | 2 | SOURCE/EVIDENCE |
| Source Date | 17 | 0 | 1 | SOURCE/EVIDENCE |
| Notes | 17 | 0 | 17 | NOTES/RESEARCH, SOURCE/EVIDENCE |

### 06_PART_MASTER

Rows: 43 · Columns: 21 · Duplicate rows: 0 · ID column: Part ID (duplicates: 0)

| Column | Non-empty | Empty | Unique | Flags |
|---|---|---|---|---|
| Part ID | 43 | 0 | 43 |  |
| Part Number | 20 | 23 | 20 |  |
| Part Name | 43 | 0 | 25 |  |
| Part Category | 43 | 0 | 8 |  |
| Part Subcategory | 43 | 0 | 15 |  |
| Component / Assembly | 43 | 0 | 16 |  |
| Genuine Hitachi Part | 43 | 0 | 4 |  |
| Consumable | 43 | 0 | 3 |  |
| Wear Part | 43 | 0 | 3 |  |
| Replacement Part | 43 | 0 | 2 |  |
| Service Part | 43 | 0 | 2 |  |
| Attachment Part | 43 | 0 | 1 |  |
| Description | 43 | 0 | 41 |  |
| Supersedes Part Number | 0 | 43 | 0 |  |
| Superseded By | 0 | 43 | 0 |  |
| Data Class | 43 | 0 | 1 | SOURCE/EVIDENCE |
| Source ID | 43 | 0 | 12 | SOURCE/EVIDENCE |
| Source URL | 43 | 0 | 12 | SOURCE/EVIDENCE, URL |
| Confidence | 43 | 0 | 1 | SOURCE/EVIDENCE |
| Source Date | 43 | 0 | 1 | SOURCE/EVIDENCE |
| Notes | 43 | 0 | 2 | NOTES/RESEARCH, SOURCE/EVIDENCE |

### 07_MACHINE_PART_FITMENT

Rows: 944 · Columns: 17 · Duplicate rows: 0 · ID column: Fitment ID (duplicates: 0)

| Column | Non-empty | Empty | Unique | Flags |
|---|---|---|---|---|
| Fitment ID | 944 | 0 | 944 |  |
| Machine ID | 944 | 0 | 78 |  |
| Machine Model | 944 | 0 | 73 |  |
| Part ID | 944 | 0 | 35 |  |
| Part Number | 68 | 876 | 20 |  |
| Part Name | 944 | 0 | 17 |  |
| Assembly | 944 | 0 | 12 |  |
| Fitment Type | 944 | 0 | 5 |  |
| Compatibility | 944 | 0 | 4 |  |
| Installation Context | 944 | 0 | 2 |  |
| Position / Location | 57 | 887 | 1 |  |
| Data Class | 944 | 0 | 2 | SOURCE/EVIDENCE |
| Source ID | 944 | 0 | 10 | SOURCE/EVIDENCE |
| Official URL | 944 | 0 | 10 | SOURCE/EVIDENCE, URL |
| Confidence | 944 | 0 | 2 | SOURCE/EVIDENCE |
| Source Date | 944 | 0 | 1 | SOURCE/EVIDENCE |
| Notes | 944 | 0 | 66 | NOTES/RESEARCH, SOURCE/EVIDENCE |

### 08_SERVICE_CAPABILITIES

Rows: 22 · Columns: 18 · Duplicate rows: 0 · ID column: Service ID (duplicates: 0)

| Column | Non-empty | Empty | Unique | Flags |
|---|---|---|---|---|
| Service ID | 22 | 0 | 22 |  |
| Service Name | 22 | 0 | 22 |  |
| Service Category | 22 | 0 | 17 |  |
| Description | 22 | 0 | 22 |  |
| Applies To Machine Category | 22 | 0 | 9 |  |
| Applies To Machine Model | 2 | 20 | 2 |  |
| Customer Site | 22 | 0 | 2 |  |
| Dealer Workshop | 22 | 0 | 2 |  |
| Other Location | 5 | 17 | 5 |  |
| Dealer Delivered | 22 | 0 | 2 |  |
| External Authorised Provider | 22 | 0 | 3 |  |
| Related Parts | 15 | 7 | 10 |  |
| Related Machine Data | 7 | 15 | 6 |  |
| Source URL | 22 | 0 | 12 | SOURCE/EVIDENCE, URL |
| Official / Derived | 22 | 0 | 1 | SOURCE/EVIDENCE |
| Source ID | 22 | 0 | 12 | SOURCE/EVIDENCE |
| Source Date | 22 | 0 | 1 | SOURCE/EVIDENCE |
| Notes | 22 | 0 | 1 | NOTES/RESEARCH, SOURCE/EVIDENCE |

### 09_MACHINE_SERVICE_MATRIX

Rows: 1694 · Columns: 20 · Duplicate rows: 0 · ID column: junction table — no per-row ID column (duplicates: 0)

| Column | Non-empty | Empty | Unique | Flags |
|---|---|---|---|---|
| Machine ID | 1694 | 0 | 77 |  |
| Machine Category | 1694 | 0 | 12 |  |
| Machine Model | 1694 | 0 | 72 |  |
| Service ID | 1694 | 0 | 22 |  |
| Service Name | 1694 | 0 | 22 |  |
| Service Type | 1694 | 0 | 17 |  |
| Applicability | 1694 | 0 | 8 |  |
| Service Location | 1694 | 0 | 3 |  |
| Trigger | 0 | 1694 | 0 |  |
| Interval (officially stated) | 308 | 1386 | 4 | SOURCE/EVIDENCE |
| Machine Hours | 0 | 1694 | 0 |  |
| Condition Based | 0 | 1694 | 0 |  |
| Dealer Service | 1694 | 0 | 2 |  |
| Workshop Service | 1694 | 0 | 2 |  |
| Field Service | 1694 | 0 | 2 |  |
| Data Class | 1694 | 0 | 1 | SOURCE/EVIDENCE |
| Source ID | 1694 | 0 | 12 | SOURCE/EVIDENCE |
| Confidence | 1694 | 0 | 2 | SOURCE/EVIDENCE |
| Source Date | 1694 | 0 | 1 | SOURCE/EVIDENCE |
| Notes | 1694 | 0 | 1 | NOTES/RESEARCH, SOURCE/EVIDENCE |

### 10_MAINTENANCE_SCHEDULE

Rows: 10 · Columns: 20 · Duplicate rows: 0 · ID column: Maintenance ID (duplicates: 0)

| Column | Non-empty | Empty | Unique | Flags |
|---|---|---|---|---|
| Maintenance ID | 10 | 0 | 10 |  |
| Machine ID | 10 | 0 | 1 |  |
| Applies To (as stated) | 10 | 0 | 9 |  |
| Maintenance Activity | 10 | 0 | 10 |  |
| Maintenance Type | 10 | 0 | 7 |  |
| Interval | 4 | 6 | 4 |  |
| Interval Unit | 4 | 6 | 1 |  |
| Operating Hours | 4 | 6 | 4 |  |
| Calendar Interval | 1 | 9 | 1 |  |
| Component | 10 | 0 | 7 |  |
| Required Part | 9 | 1 | 8 |  |
| Required Quantity | 0 | 10 | 0 |  |
| Consumable | 10 | 0 | 2 |  |
| Service Description / Official Wording | 10 | 0 | 10 | SOURCE/EVIDENCE |
| Data Class | 10 | 0 | 2 | SOURCE/EVIDENCE |
| Source ID | 10 | 0 | 7 | SOURCE/EVIDENCE |
| Source URL | 10 | 0 | 7 | SOURCE/EVIDENCE, URL |
| Confidence | 10 | 0 | 3 | SOURCE/EVIDENCE |
| Source Date | 10 | 0 | 1 | SOURCE/EVIDENCE |
| Notes | 10 | 0 | 1 | NOTES/RESEARCH, SOURCE/EVIDENCE, URL |

### 11_SERVICE_PART_REQUIREMENTS

Rows: 11 · Columns: 17 · Duplicate rows: 0 · ID column: Requirement ID (duplicates: 0)

| Column | Non-empty | Empty | Unique | Flags |
|---|---|---|---|---|
| Requirement ID | 11 | 0 | 11 |  |
| Machine ID | 11 | 0 | 1 |  |
| Service ID | 11 | 0 | 8 |  |
| Service Name | 11 | 0 | 8 |  |
| Maintenance Activity | 11 | 0 | 8 |  |
| Part ID | 11 | 0 | 7 |  |
| Part Number | 0 | 11 | 0 |  |
| Part Name | 11 | 0 | 7 |  |
| Quantity | 1 | 10 | 1 |  |
| Mandatory / Optional | 11 | 0 | 2 |  |
| Consumable / Wear / Replacement | 11 | 0 | 2 |  |
| Data Class | 11 | 0 | 1 | SOURCE/EVIDENCE |
| Source ID | 11 | 0 | 7 | SOURCE/EVIDENCE |
| Source URL | 11 | 0 | 7 | SOURCE/EVIDENCE, URL |
| Confidence | 11 | 0 | 3 | SOURCE/EVIDENCE |
| Source Date | 11 | 0 | 1 | SOURCE/EVIDENCE |
| Notes | 11 | 0 | 11 | NOTES/RESEARCH, SOURCE/EVIDENCE |

### 12_MACHINE_DIGITAL_SERVICES

Rows: 616 · Columns: 20 · Duplicate rows: 0 · ID column: junction table — no per-row ID column (duplicates: 0)

| Column | Non-empty | Empty | Unique | Flags |
|---|---|---|---|---|
| Digital Service ID | 616 | 0 | 8 |  |
| Service Name | 616 | 0 | 8 |  |
| Machine ID | 616 | 0 | 77 |  |
| Machine Model | 616 | 0 | 72 |  |
| Machine Category | 616 | 0 | 12 |  |
| Applicability | 616 | 0 | 2 |  |
| Capability | 616 | 0 | 8 |  |
| Machine Data | 616 | 0 | 8 |  |
| Alert / Monitoring | 616 | 0 | 7 |  |
| Maintenance Support | 616 | 0 | 5 |  |
| Diagnostic Support | 616 | 0 | 2 |  |
| Parts Support | 616 | 0 | 3 |  |
| Dealer Support | 616 | 0 | 2 |  |
| Description | 616 | 0 | 8 |  |
| Stated Applicability (official wording) | 616 | 0 | 8 | SOURCE/EVIDENCE |
| Data Class | 616 | 0 | 1 | SOURCE/EVIDENCE |
| Source ID | 616 | 0 | 6 | SOURCE/EVIDENCE |
| URL | 616 | 0 | 6 | URL |
| Source Date | 616 | 0 | 1 | SOURCE/EVIDENCE |
| Notes | 616 | 0 | 1 | NOTES/RESEARCH, SOURCE/EVIDENCE |

### 13_AFTER_SALES_RELATIONSHIPS

Rows: 3283 · Columns: 14 · Duplicate rows: 0 · ID column: Relationship ID (duplicates: 0)

| Column | Non-empty | Empty | Unique | Flags |
|---|---|---|---|---|
| Relationship ID | 3283 | 0 | 3283 |  |
| From Entity Type | 3283 | 0 | 5 |  |
| From ID | 3283 | 0 | 135 |  |
| From Name | 3283 | 0 | 132 |  |
| Relationship | 3283 | 0 | 13 |  |
| To Entity Type | 3283 | 0 | 5 |  |
| To ID | 3266 | 17 | 84 |  |
| To Name | 3283 | 0 | 77 |  |
| Data Class | 3283 | 0 | 2 | SOURCE/EVIDENCE |
| Source ID | 3283 | 0 | 38 | SOURCE/EVIDENCE |
| Source URL | 3283 | 0 | 38 | SOURCE/EVIDENCE, URL |
| Confidence | 3283 | 0 | 3 | SOURCE/EVIDENCE |
| Source Date | 3283 | 0 | 1 | SOURCE/EVIDENCE |
| Notes | 3283 | 0 | 55 | NOTES/RESEARCH, SOURCE/EVIDENCE |

### 14_SOURCE_REGISTER

Rows: 47 · Columns: 10 · Duplicate rows: 0 · ID column: — (duplicates: 0)

| Column | Non-empty | Empty | Unique | Flags |
|---|---|---|---|---|
| Source ID | 47 | 0 | 47 | SOURCE/EVIDENCE |
| Source Organisation | 47 | 0 | 3 | SOURCE/EVIDENCE |
| Source Type | 47 | 0 | 14 | SOURCE/EVIDENCE |
| URL | 47 | 0 | 46 | URL |
| Page Title | 47 | 0 | 47 |  |
| Machine / Category | 47 | 0 | 26 |  |
| Data Domain | 47 | 0 | 42 |  |
| Date Accessed | 47 | 0 | 1 | SOURCE/EVIDENCE |
| Official Source | 47 | 0 | 2 | SOURCE/EVIDENCE |
| Notes | 47 | 0 | 2 | NOTES/RESEARCH, SOURCE/EVIDENCE |

### 15_DATA_QUALITY

Rows: 40 · Columns: 9 · Duplicate rows: 0 · ID column: junction table — no per-row ID column (duplicates: 0)

| Column | Non-empty | Empty | Unique | Flags |
|---|---|---|---|---|
| Entity | 40 | 0 | 9 |  |
| Record ID | 40 | 0 | 30 |  |
| Field | 40 | 0 | 17 |  |
| Value | 33 | 7 | 16 |  |
| Source | 40 | 0 | 12 | SOURCE/EVIDENCE |
| Confidence | 40 | 0 | 4 | SOURCE/EVIDENCE |
| Status | 40 | 0 | 7 |  |
| Missing / Unknown Reason | 39 | 1 | 19 |  |
| Validation Note | 40 | 0 | 20 | NOTES/RESEARCH, URL |

### 16_CATEGORY_COMPARISON

Rows: 12 · Columns: 16 · Duplicate rows: 0 · ID column: Category ID (duplicates: 0)

| Column | Non-empty | Empty | Unique | Flags |
|---|---|---|---|---|
| Category | 12 | 0 | 12 |  |
| Category ID | 12 | 0 | 12 |  |
| Typical Machine Type | 12 | 0 | 12 |  |
| Machine Count | 12 | 0 | 7 |  |
| Machine Count (live formula) | 0 | 12 | 0 |  |
| Main Applications | 12 | 0 | 12 |  |
| Common Attachments | 11 | 1 | 11 |  |
| Common Parts Characteristics | 12 | 0 | 10 |  |
| Common Service Characteristics | 12 | 0 | 8 |  |
| Machine-Specific Service Characteristics | 12 | 0 | 12 |  |
| Digital Services | 11 | 1 | 7 |  |
| Key Technical Differences | 12 | 0 | 12 |  |
| After-Sales Differences | 12 | 0 | 10 |  |
| Published Specification Groups (frequency) | 12 | 0 | 12 |  |
| Source ID | 12 | 0 | 7 | SOURCE/EVIDENCE |
| Source Date | 12 | 0 | 1 | SOURCE/EVIDENCE |

### 17_COMMON_VS_SPECIFIC

Rows: 34 · Columns: 8 · Duplicate rows: 0 · ID column: Analysis ID (duplicates: 0)

| Column | Non-empty | Empty | Unique | Flags |
|---|---|---|---|---|
| Analysis ID | 34 | 0 | 34 |  |
| Capability | 34 | 0 | 34 |  |
| Classification | 34 | 0 | 11 |  |
| Evidence / Finding | 34 | 0 | 34 |  |
| Source URL | 34 | 0 | 25 | SOURCE/EVIDENCE, URL |
| Source ID | 34 | 0 | 25 | SOURCE/EVIDENCE |
| Confidence | 34 | 0 | 2 | SOURCE/EVIDENCE |
| Source Date | 34 | 0 | 1 | SOURCE/EVIDENCE |

### 18_DATA_DICTIONARY

Rows: 68 · Columns: 10 · Duplicate rows: 0 · ID column: — (duplicates: 0)

| Column | Non-empty | Empty | Unique | Flags |
|---|---|---|---|---|
| Table Name | 68 | 0 | 16 |  |
| Field Name | 68 | 0 | 54 |  |
| Data Type | 68 | 0 | 17 |  |
| Required? | 68 | 0 | 2 |  |
| Primary Key? | 68 | 0 | 2 |  |
| Foreign Key? | 68 | 0 | 7 |  |
| Description | 68 | 0 | 64 |  |
| Example | 68 | 0 | 53 | URL |
| Source Sheet | 68 | 0 | 15 | SOURCE/EVIDENCE |
| Notes | 68 | 0 | 2 | NOTES/RESEARCH, SOURCE/EVIDENCE |

### 19_RELATIONSHIP_SCHEMA

Rows: 18 · Columns: 8 · Duplicate rows: 0 · ID column: Schema ID (duplicates: 0)

| Column | Non-empty | Empty | Unique | Flags |
|---|---|---|---|---|
| Schema ID | 18 | 0 | 18 |  |
| From Entity | 18 | 0 | 8 |  |
| Cardinality | 18 | 0 | 4 |  |
| To Entity | 18 | 0 | 14 |  |
| Implementation | 18 | 0 | 18 |  |
| Evidence Class | 17 | 1 | 9 |  |
| Design Note | 18 | 0 | 18 | NOTES/RESEARCH |
| Source ID | 17 | 1 | 13 | SOURCE/EVIDENCE |

### 20_COMPLETENESS_CHECK

Rows: 33 · Columns: 6 · Duplicate rows: 0 · ID column: Check ID (duplicates: 0)

| Column | Non-empty | Empty | Unique | Flags |
|---|---|---|---|---|
| Check ID | 23 | 10 | 23 |  |
| Metric | 32 | 1 | 32 |  |
| Count | 22 | 11 | 21 |  |
| Sheet | 32 | 1 | 26 |  |
| Note | 22 | 11 | 22 | NOTES/RESEARCH |
| Source Date | 22 | 11 | 1 | SOURCE/EVIDENCE |