"""Tests for validate_record in src/data_pipeline/validation.py."""
import pytest

from src.data_pipeline.models import NormalizedQuery
from src.data_pipeline.validation import validate_record


def _make_record(**overrides) -> NormalizedQuery:
    defaults = dict(
        id="1",
        source="synthetic",
        domain="general",
        dialect="duckdb",
        database_id="test_db",
        nl_question="How many users are there?",
        ground_truth_sql="SELECT COUNT(*) FROM users",
        ddl="CREATE TABLE users (id INT);",
    )
    defaults.update(overrides)
    return NormalizedQuery(**defaults)


def test_valid_record_has_no_errors():
    record = _make_record()
    assert validate_record(record) == []


def test_missing_id():
    record = _make_record(id="")
    errors = validate_record(record)
    assert any("missing id" in e for e in errors)


def test_missing_source():
    record = _make_record(source="")
    errors = validate_record(record)
    assert any("missing source" in e for e in errors)


def test_missing_question():
    record = _make_record(nl_question="")
    errors = validate_record(record)
    assert any("missing question" in e for e in errors)


def test_missing_sql():
    record = _make_record(ground_truth_sql="")
    errors = validate_record(record)
    assert any("missing SQL" in e for e in errors)


def test_missing_database_id():
    record = _make_record(database_id="")
    errors = validate_record(record)
    assert any("missing database_id" in e for e in errors)


def test_missing_dialect():
    record = _make_record(dialect="")
    errors = validate_record(record)
    assert any("missing dialect" in e for e in errors)


def test_missing_ddl():
    record = _make_record(ddl="")
    errors = validate_record(record)
    assert any("missing DDL" in e for e in errors)


def test_question_too_short():
    record = _make_record(nl_question="Hi")
    errors = validate_record(record)
    assert any("question too short" in e for e in errors)


def test_sql_too_short():
    record = _make_record(ground_truth_sql="X")
    errors = validate_record(record)
    assert any("SQL too short" in e for e in errors)


def test_multiple_errors_accumulated():
    """Validation collects ALL errors, not just the first one."""
    record = _make_record(nl_question="", ground_truth_sql="", ddl="")
    errors = validate_record(record)
    assert len(errors) >= 3
