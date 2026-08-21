"""
STEP 33 — Integration test.

Verifies the full normalization pipeline end-to-end:
  raw record → adapter → normalizer → validator → dedup → final record
"""
import pytest

from src.data_pipeline.dedup import deduplicate
from src.data_pipeline.pipeline import normalize_record
from src.data_pipeline.validation import validate_record


# ── Fixtures ─────────────────────────────────────────────────────────────────

SPIDER_RAW = {
    "question": "How many singers are there?",
    "query": "SELECT COUNT(*) FROM singer",
    "db_id": "concert_singer",
    "ddl": "CREATE TABLE singer (id INT, name TEXT);",
}

BIRD_RAW = {
    "prompt": "List all financial accounts",
    "SQL": "SELECT * FROM accounts;",
    "db_id": "financial_db",
    "dialect": "postgresql",
    "ddl": "CREATE TABLE accounts (id INT, balance DECIMAL);",
    "domain": "finance",
}

SYNTHETIC_RAW = {
    "question": "How many users?",
    "sql": "SELECT COUNT(*) FROM users",
    "database_id": "shop",
    "ddl": """
        CREATE TABLE users (
            id INTEGER,
            name VARCHAR
        )
    """,
    "domain": "ecommerce",
    "dialect": "sqlite",
}


# ── Core integration test (STEP 33) ──────────────────────────────────────────

def test_full_normalization_pipeline():
    raw = {
        "question": "How many users?",
        "sql": "SELECT COUNT(*) FROM users",
        "db_id": "shop",
        "ddl": """
            CREATE TABLE users (
                id INTEGER,
                name VARCHAR
            )
        """,
        "domain": "ecommerce",
        "dialect": "sqlite",
    }

    record = normalize_record("synthetic", raw, 0)
    errors = validate_record(record)

    assert errors == []
    assert record.source == "synthetic"
    assert record.database_id == "shop"
    assert record.nl_question
    assert record.ground_truth_sql
    assert record.ddl


# ── Per-source pipeline tests ─────────────────────────────────────────────────

def test_spider_pipeline():
    record = normalize_record("spider", SPIDER_RAW, 0)
    errors = validate_record(record)
    assert errors == [], f"Unexpected errors: {errors}"
    assert record.source == "spider"
    assert record.dialect == "sqlite"
    assert record.database_id == "concert_singer"
    assert "COUNT" in record.ground_truth_sql


def test_bird_pipeline():
    record = normalize_record("bird", BIRD_RAW, 0)
    errors = validate_record(record)
    assert errors == [], f"Unexpected errors: {errors}"
    assert record.source == "bird"
    assert record.dialect == "postgresql"
    assert record.domain == "finance"
    assert record.database_id == "financial_db"


def test_synthetic_pipeline():
    record = normalize_record("synthetic", SYNTHETIC_RAW, 0)
    errors = validate_record(record)
    assert errors == [], f"Unexpected errors: {errors}"
    assert record.source == "synthetic"
    assert record.domain == "ecommerce"
    assert record.dialect == "sqlite"
    assert record.database_id == "shop"


# ── Dedup integration ─────────────────────────────────────────────────────────

def test_pipeline_then_dedup_removes_duplicate():
    record = normalize_record("synthetic", SYNTHETIC_RAW, 0)
    duplicate = normalize_record("synthetic", SYNTHETIC_RAW, 1)
    result = deduplicate([record, duplicate])
    assert len(result) == 1


def test_pipeline_then_dedup_keeps_distinct():
    r1 = normalize_record("spider", SPIDER_RAW, 0)
    r2 = normalize_record("bird", BIRD_RAW, 1)
    r3 = normalize_record("synthetic", SYNTHETIC_RAW, 2)
    result = deduplicate([r1, r2, r3])
    assert len(result) == 3


# ── Invalid records are caught before dedup ───────────────────────────────────

def test_invalid_record_rejected_by_validator():
    """The normalizer raises ValueError for a missing SQL query before validation runs."""
    bad_raw = {
        "question": "q",
        "sql": "",          # missing SQL → normalizer raises ValueError
        "database_id": "db",
        "ddl": "CREATE TABLE t (id INT);",
    }
    with pytest.raises(ValueError, match="missing a SQL query"):
        normalize_record("synthetic", bad_raw, 0)



def test_missing_ddl_rejected_by_validator():
    bad_raw = {
        "question": "How many rows?",
        "sql": "SELECT COUNT(*) FROM t",
        "database_id": "db",
        "ddl": "",          # missing DDL → should fail validation
    }
    record = normalize_record("synthetic", bad_raw, 0)
    errors = validate_record(record)
    assert any("DDL" in e for e in errors)


# ── Output shape ──────────────────────────────────────────────────────────────

def test_normalized_record_has_all_required_fields():
    record = normalize_record("synthetic", SYNTHETIC_RAW, 0)
    assert record.id
    assert record.source
    assert record.domain
    assert record.dialect
    assert record.database_id
    assert record.nl_question
    assert record.ground_truth_sql
    assert record.ddl
