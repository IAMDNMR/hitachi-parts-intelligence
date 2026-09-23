"""
tests/test_audit_workbook.py
=============================================================================
Unit and integration test suite for audit_workbook.py.
Covers CLI options, exit code contracts, immutability, determinism,
metric extraction, and Neo4j isolation guardrails.
=============================================================================
"""

import hashlib
import os
from pathlib import Path
import subprocess
import sys
from typing import Set
import pytest

import audit_workbook
from audit_workbook import (
    calculate_sha256,
    infer_cell_type,
    detect_sentinel_value,
    check_url_leakage,
    classify_column_utility,
    detect_full_duplicate_rows,
    analyze_primary_key_uniqueness,
    DEFAULT_SOURCE_PATH,
    DEFAULT_OUTPUT_PATH,
)

SCRIPT_PATH = Path("audit_workbook.py").resolve()


# =============================================================================
# UNIT TESTS: METRIC EXTRACTION & COMPUTATIONAL HELPERS
# =============================================================================

class TestMetricExtractionHelpers:
    """Unit tests for metric extraction and classification algorithms."""

    def test_infer_cell_type_bool_precedence(self):
        """Python bool is a subclass of int; bool must be checked before int."""
        assert infer_cell_type(True) == "bool"
        assert infer_cell_type(False) == "bool"
        assert infer_cell_type(42) == "int"
        assert infer_cell_type(3.14) == "float"
        assert infer_cell_type("hitachi") == "str"
        assert infer_cell_type(None) == "NoneType"

    def test_detect_sentinel_value(self):
        """Detects canonical sentinel values and ignores normal content."""
        is_sent, name = detect_sentinel_value("NOT PUBLICLY STATED")
        assert is_sent and name == "NOT PUBLICLY STATED"

        is_sent, name = detect_sentinel_value("N/A")
        assert is_sent and name == "N/A"

        is_sent, name = detect_sentinel_value("-")
        assert is_sent and name == "-"

        is_sent, name = detect_sentinel_value("TBD")
        assert is_sent and name == "TBD"

        is_sent, _ = detect_sentinel_value("Diesel Engine 140 kW")
        assert not is_sent

        is_sent, _ = detect_sentinel_value(12345)
        assert not is_sent

    def test_check_url_leakage(self):
        """Detects full URLs while avoiding false positives on model codes and numbers."""
        has_url, matches = check_url_leakage("https://www.hitachicm.com/eu/en/machinery/excavators/zx250-7.html")
        assert has_url
        assert len(matches) >= 1

        has_url, matches = check_url_leakage("www.hitachicm.eu")
        assert has_url

        # False positive guards
        has_url, _ = check_url_leakage("ZX250-7")
        assert not has_url

        has_url, _ = check_url_leakage("ZX330LC-5G")
        assert not has_url

        has_url, _ = check_url_leakage("32.5")
        assert not has_url

        has_url, _ = check_url_leakage("CAT-EXC")
        assert not has_url

    def test_classify_column_utility(self):
        """Tests 5-class column classification rules."""
        # Noise
        cat, _, _ = classify_column_utility("ui_search_rank", {"int"}, 0, 77, "03_MACHINE_SPECIFICATIONS")
        assert cat == "NOISE_TO_REMOVE"

        cat, _, _ = classify_column_utility("featured_badge", {"bool"}, 0, 77, "03_MACHINE_SPECIFICATIONS")
        assert cat == "NOISE_TO_REMOVE"

        # Provenance
        cat, _, _ = classify_column_utility("source_url", {"str"}, 77, 77, "02_MACHINE_MASTER")
        assert cat == "PROVENANCE_METADATA"

        # Graph Relationship Pointer
        cat, _, _ = classify_column_utility("category_id", {"str"}, 0, 77, "02_MACHINE_MASTER")
        assert cat == "GRAPH_RELATIONSHIP_POINTER"

        # Controlled Vocab
        cat, _, _ = classify_column_utility("fitment_evidence", {"str"}, 0, 449, "07_MACHINE_PART_FITMENT")
        assert cat == "CONTROLLED_VOCAB_FIELD"

        # Technical Entity Attribute (Entity PK)
        cat, _, _ = classify_column_utility("machine_id", {"str"}, 0, 77, "02_MACHINE_MASTER")
        assert cat == "TECHNICAL_ENTITY_ATTRIBUTE"

        # Technical Entity Attribute (Engineering property)
        cat, _, _ = classify_column_utility("rated_power_kw", {"float"}, 0, 77, "03_MACHINE_SPECIFICATIONS")
        assert cat == "TECHNICAL_ENTITY_ATTRIBUTE"

    def test_detect_full_duplicate_rows(self):
        """Detects full duplicate row instances correctly."""
        rows = [
            ("A", 1, 2.5),
            ("B", 2, 3.5),
            ("A", 1, 2.5), # duplicate of row 0
            ("C", 3, 4.5),
            ("B", 2, 3.5), # duplicate of row 1
        ]
        dup_count = detect_full_duplicate_rows(rows)
        assert dup_count == 2

    def test_analyze_primary_key_uniqueness(self):
        """Verifies candidate PK uniqueness analysis and collision detection."""
        rows_unique = [
            ("MC-001", "Model A"),
            ("MC-002", "Model B"),
            ("MC-003", "Model C"),
        ]
        is_uniq, dups, samples = analyze_primary_key_uniqueness(rows_unique, 1, "machine_id")
        assert is_uniq
        assert dups == 0
        assert len(samples) == 0

        rows_dups = [
            ("MC-001", "Model A"),
            ("MC-001", "Model A duplicate"),
            ("MC-002", "Model B"),
            ("MC-002", "Model B duplicate"),
        ]
        is_uniq, dups, samples = analyze_primary_key_uniqueness(rows_dups, 1, "machine_id")
        assert not is_uniq
        assert dups == 2
        assert sorted(samples) == ["MC-001", "MC-002"]


# =============================================================================
# INTEGRATION TESTS: CLI & EXIT CODE CONTRACT
# =============================================================================

class TestAuditWorkbookCLI:
    """Test suite verifying CLI options and exit code contracts."""

    def test_bad_arguments_exit_code_1(self):
        """Exit code 1 on unrecognized argument or invalid flag."""
        cmd = [sys.executable, str(SCRIPT_PATH), "--invalid-nonexistent-flag"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 1
        assert "ERROR [BAD_ARGUMENTS]" in res.stderr or "unrecognized arguments" in res.stderr

    def test_missing_source_exit_code_2(self, tmp_path):
        """Exit code 2 when source file does not exist."""
        non_existent = tmp_path / "does_not_exist.xlsx"
        cmd = [sys.executable, str(SCRIPT_PATH), "-i", str(non_existent)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 2
        assert "ERROR [MISSING_SOURCE]" in res.stderr

    def test_corrupt_source_exit_code_2(self, tmp_path):
        """Exit code 2 when source file is not a valid zip/xlsx archive."""
        corrupt_file = tmp_path / "corrupt.xlsx"
        corrupt_file.write_bytes(b"NOT_A_VALID_ZIP_ARCHIVE_HEADER")
        cmd = [sys.executable, str(SCRIPT_PATH), "-i", str(corrupt_file)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 2

    def test_version_flag_exit_code_0(self):
        """Exit code 0 when invoked with --version."""
        cmd = [sys.executable, str(SCRIPT_PATH), "--version"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0
        assert "1.0.0" in res.stdout or "1.0.0" in res.stderr

    def test_help_flag_exit_code_0(self):
        """Exit code 0 when invoked with --help."""
        cmd = [sys.executable, str(SCRIPT_PATH), "--help"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0
        assert "Hitachi OEM After-Sales" in res.stdout
        assert "Exit Codes:" in res.stdout


# =============================================================================
# GUARDRAIL & DETERMINISM TESTS
# =============================================================================

class TestGuardrailsAndDeterminism:
    """Tests strictly verifying security guardrails and byte-level determinism."""

    def test_neo4j_isolation_guardrail(self):
        """audit_workbook.py must not import neo4j, py2neo, or connect to port 7687."""
        code = SCRIPT_PATH.read_text(encoding="utf-8")
        assert "import neo4j" not in code
        assert "from neo4j" not in code
        assert "py2neo" not in code
        assert "7687" not in code

    def test_no_dynamic_datetime_now(self):
        """audit_workbook.py must not inject datetime.now() into generated output."""
        code = SCRIPT_PATH.read_text(encoding="utf-8")
        assert "datetime.now()" not in code
        assert "datetime.utcnow()" not in code

    def test_source_immutability_and_double_run_determinism(self, tmp_path):
        """
        If the authoritative source workbook exists:
          1. Pre- and post-read SHA-256 and mtime must remain identical.
          2. Double run must produce bit-for-bit identical markdown files.
        """
        if not DEFAULT_SOURCE_PATH.exists():
            pytest.skip(f"Source file not present at {DEFAULT_SOURCE_PATH}")

        # Baseline capture
        stat_before = DEFAULT_SOURCE_PATH.stat()
        hash_before = calculate_sha256(DEFAULT_SOURCE_PATH)

        out1 = tmp_path / "audit_run1.md"
        out2 = tmp_path / "audit_run2.md"

        cmd1 = [sys.executable, str(SCRIPT_PATH), "-i", str(DEFAULT_SOURCE_PATH), "-o", str(out1), "-q"]
        res1 = subprocess.run(cmd1, capture_output=True, text=True)
        assert res1.returncode == 0, f"Run 1 failed: {res1.stderr}"

        cmd2 = [sys.executable, str(SCRIPT_PATH), "-i", str(DEFAULT_SOURCE_PATH), "-o", str(out2), "-q"]
        res2 = subprocess.run(cmd2, capture_output=True, text=True)
        assert res2.returncode == 0, f"Run 2 failed: {res2.stderr}"

        # Assert immutability
        stat_after = DEFAULT_SOURCE_PATH.stat()
        hash_after = calculate_sha256(DEFAULT_SOURCE_PATH)
        assert hash_before == hash_after, "FATAL: Source workbook hash modified!"
        assert stat_before.st_mtime_ns == stat_after.st_mtime_ns, "FATAL: Source timestamp modified!"

        # Assert byte determinism
        content1 = out1.read_bytes()
        content2 = out2.read_bytes()
        assert content1 == content2, "FATAL: Double-run produced non-identical markdown outputs!"
        assert len(content1) > 1000

        # Assert all 21 sheets covered
        text1 = out1.read_text(encoding="utf-8")
        for i in range(21):
            assert f"## Sheet {i:02d}:" in text1
