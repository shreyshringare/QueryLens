"""Tests for deduplication in src/data_pipeline/dedup.py."""
from src.data_pipeline.dedup import deduplicate, record_fingerprint
from src.data_pipeline.models import NormalizedQuery


def _rec(question: str, sql: str, db_id: str = "db", uid: str = "1") -> NormalizedQuery:
    return NormalizedQuery(
        id=uid,
        source="synthetic",
        domain="general",
        dialect="duckdb",
        database_id=db_id,
        nl_question=question,
        ground_truth_sql=sql,
        ddl="CREATE TABLE t (id INT);",
    )


def test_fingerprint_is_deterministic():
    r = _rec("How many users?", "SELECT COUNT(*) FROM users")
    assert record_fingerprint(r) == record_fingerprint(r)


def test_fingerprint_differs_by_question():
    r1 = _rec("How many users?", "SELECT COUNT(*) FROM users")
    r2 = _rec("How many items?", "SELECT COUNT(*) FROM users")
    assert record_fingerprint(r1) != record_fingerprint(r2)


def test_fingerprint_differs_by_sql():
    r1 = _rec("q", "SELECT 1")
    r2 = _rec("q", "SELECT 2")
    assert record_fingerprint(r1) != record_fingerprint(r2)


def test_fingerprint_differs_by_database_id():
    r1 = _rec("q", "SELECT 1", db_id="db_a")
    r2 = _rec("q", "SELECT 1", db_id="db_b")
    assert record_fingerprint(r1) != record_fingerprint(r2)


def test_fingerprint_case_insensitive():
    """Fingerprint normalises case so 'SELECT' == 'select'."""
    r1 = _rec("How many users?", "SELECT COUNT(*) FROM users")
    r2 = _rec("how many users?", "select count(*) from users")
    assert record_fingerprint(r1) == record_fingerprint(r2)


def test_deduplicate_removes_exact_duplicates():
    r = _rec("How many users?", "SELECT COUNT(*) FROM users")
    records = [r, r, r]
    result = deduplicate(records)
    assert len(result) == 1


def test_deduplicate_keeps_distinct_records():
    records = [
        _rec("Q1", "SELECT 1", uid="1"),
        _rec("Q2", "SELECT 2", uid="2"),
        _rec("Q3", "SELECT 3", uid="3"),
    ]
    result = deduplicate(records)
    assert len(result) == 3


def test_deduplicate_keeps_first_occurrence():
    r1 = _rec("q", "SELECT 1", uid="first")
    r2 = _rec("q", "SELECT 1", uid="second")
    result = deduplicate([r1, r2])
    assert len(result) == 1
    assert result[0].id == "first"


def test_deduplicate_empty_list():
    assert deduplicate([]) == []


def test_deduplicate_mixed_case_treated_as_duplicate():
    r1 = _rec("How many users?", "SELECT COUNT(*) FROM users")
    r2 = _rec("HOW MANY USERS?", "select count(*) from users")
    result = deduplicate([r1, r2])
    assert len(result) == 1
