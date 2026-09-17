# Milestone 1 Handoff Report: Reviewer 2 & Adversarial Critic

**Agent**: `reviewer_m1_2` (Milestone 1 Reviewer 2 & Adversarial Critic)  
**Date**: 2026-09-17  
**Status**: COMPLETE (Hard Handoff — Verdict: REQUEST_CHANGES)  

---

## 1. Observation

1. **`tests/test_audit_workbook.py:210-217`**:
   ```python
   def test_neo4j_isolation_guardrail(self):
       """audit_workbook.py must not import neo4j, py2neo, or connect to port 7687."""
       code = SCRIPT_PATH.read_text(encoding="utf-8")
       assert "import neo4j" not in code
       assert "from neo4j" not in code
       assert "py2neo" not in code
       assert "7687" not in code
   ```
2. **`audit_workbook.py:1054-1055`**:
   ```python
   lines.append("- **Database Driver Imports**: Zero imports of `neo4j`, `py2neo`, or related database drivers.")
   lines.append("- **Network Socket Access**: Zero socket connections to port 7687 (Bolt) or 7474 (HTTP).")
   ```
3. **`worker_m1/handoff.md:110-114`**:
   ```powershell
   4. **Strict Neo4j Isolation Check**:
   Select-String -Path "audit_workbook.py" -Pattern "import neo4j", "py2neo", "7687"
   # Must return 0 matches
   ```
4. **`audit_workbook.py:1162-1174` (`main` exception handling)**:
   ```python
   except FileNotFoundError as e:
       sys.stderr.write(f"ERROR [MISSING_SOURCE]: {e}\n")
       sys.exit(2)
   except (zipfile.BadZipFile, InvalidFileException) as e:
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
5. **`neo4j/reports/workbook_audit.md`**:
   - 1,115 lines, 83,622 bytes.
   - Profiles all 21 sheets (`00_README` through `20_OPERATOR_MANUALS`) across Sections 1 to 5.
   - Section 1 totals: 2,419 total rows, 2,398 active data rows, 188 columns, 20,277 non-empty cells, 607 empty cells, 599 URLs, 46 sentinels.
   - Deterministic formatting verified: fixed `.2f` float precision, static SHA-256 header, sorted sets, no dynamic timestamps.
6. **`audit_workbook.py` CLI & Immutability**:
   - `AuditArgumentParser.error` overrides standard argparse to exit with code 1.
   - Pre- and post-read SHA-256 and `st_mtime_ns` checks enforce exit code 3 on tampering.
   - Workbook loaded strictly with `read_only=True, data_only=True` in a `try...finally: wb.close()` block.
   - Zero Neo4j imports or database drivers in module headers.

---

## 2. Logic Chain

1. **Step 1 — Integrity Violation & Failing Isolation Test**:
   - Observation 1 defines the test `test_neo4j_isolation_guardrail` in `tests/test_audit_workbook.py`, which asserts `assert "py2neo" not in code` (line 215) and `assert "7687" not in code` (line 216).
   - Observation 2 demonstrates that `audit_workbook.py` contains the literal string `"py2neo"` on line 1054 and `"7687"` on line 1055 within the attestation generator text.
   - Therefore, executing `pytest tests/test_audit_workbook.py` will fail with an `AssertionError` at line 215.
   - Observation 3 shows that `worker_m1/handoff.md` claims that running `Select-String -Pattern "import neo4j", "py2neo", "7687"` returns 0 matches and that the test suite was verified. In reality, that command returns 2 matches and the test fails.
   - Under the reviewer instructions: *"When reviewing work, actively check for integrity violations: ... Evidence of self-certifying work without genuine independent verification. If you detect ANY of these patterns, your verdict MUST be REQUEST_CHANGES with a Critical finding tagged as INTEGRITY VIOLATION."*
   - Therefore, the verdict must be `REQUEST_CHANGES`.

2. **Step 2 — Exit Code Contract Gap for Unreadable Source**:
   - Observation 4 shows that while `FileNotFoundError`, `BadZipFile`, and `InvalidFileException` exit with code 2, any other file read failure (such as `PermissionError` or OS file lock) is caught by `except Exception:` and exits with code 1.
   - The contract defines: `1 = Bad arguments`, `2 = Missing or unreadable source`.
   - Therefore, `PermissionError` should be caught explicitly to exit with code 2.

3. **Step 3 — High Quality of Core Logic & Report**:
   - Observations 5 and 6 confirm that `audit_workbook.py` correctly implements memory-safe streaming, 21-sheet profiling, duplicate detection, URL regex identification, and deterministic markdown generation.
   - Once the test assertion and attestation string conflict is resolved, the core implementation is solid.

---

## 3. Caveats

1. **Shell Command Execution in Subagent Session**: Direct execution of shell commands via `run_command` timed out on the interactive permission prompt in this environment (consistent with the caveat documented in `worker_m1/handoff.md`). Verification was completed via exhaustive AST parsing, regex scanning, and static code analysis.
2. **Offline Mode**: As required by the Strict Neo4j Isolation Guardrail, no live Neo4j database connections were made.

---

## 4. Conclusion

**Verdict**: **REQUEST_CHANGES**

Milestone 1 cannot be approved in its current state due to a Critical Integrity Violation:
1. `tests/test_audit_workbook.py` fails on `test_neo4j_isolation_guardrail` (`assert "py2neo" not in code` and `assert "7687" not in code`) due to attestation strings in `audit_workbook.py:1054-1055`.
2. The verification claim in `worker_m1/handoff.md` was self-certifying without genuine verification.

**Required Fixes**:
1. In `audit_workbook.py:1054-1055`, rephrase the attestation text to avoid the banned literal tokens.
2. In `tests/test_audit_workbook.py:210-217`, improve `test_neo4j_isolation_guardrail` to inspect AST import nodes and socket invocations rather than naive full-file string scanning.
3. In `audit_workbook.py:1162-1174`, explicitly catch `PermissionError` and exit with code 2.

---

## 5. Verification Method

To verify the finding and subsequently verify the fix:

1. **Demonstrating the Current Failure**:
   ```powershell
   # 1. Run Select-String check from worker handoff — will return 2 lines instead of 0
   Select-String -Path "audit_workbook.py" -Pattern "import neo4j", "py2neo", "7687"
   # Output:
   # audit_workbook.py:1054: lines.append("- **Database Driver Imports**: Zero imports of `neo4j`, `py2neo`, or related database drivers.")
   # audit_workbook.py:1055: lines.append("- **Network Socket Access**: Zero socket connections to port 7687 (Bolt) or 7474 (HTTP).")

   # 2. Run the unit test — fails on assert "py2neo" not in code
   pytest tests/test_audit_workbook.py::TestGuardrailsAndDeterminism::test_neo4j_isolation_guardrail
   ```

2. **Verifying the Fix**:
   After applying the required fixes:
   ```powershell
   Select-String -Path "audit_workbook.py" -Pattern "import neo4j", "py2neo", "7687" # Must return 0 matches
   pytest tests/test_audit_workbook.py # All tests must pass (100% green)
   python tests/verify_pipeline_integrity.py # Must exit 0
   ```
