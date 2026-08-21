"""Tests for SyntheticAdapter."""
from src.data_pipeline.adapters import SyntheticAdapter


def test_synthetic_adapt_basic():
    raw = {
        "question": "How many users are there?",
        "sql": "SELECT COUNT(*) FROM users",
        "database_id": "shop",
        "ddl": "CREATE TABLE users (id INT, name VARCHAR);",
        "domain": "ecommerce",
        "dialect": "duckdb",
    }
    result = SyntheticAdapter().adapt(raw)

    assert result["question"] == "How many users are there?"
    assert result["query"] == "SELECT COUNT(*) FROM users"
    assert result["db_id"] == "shop"
    assert result["ddl"] == "CREATE TABLE users (id INT, name VARCHAR);"
    assert result["domain"] == "ecommerce"
    assert result["dialect"] == "duckdb"


def test_synthetic_question_nl_question_fallback():
    """Synthetic records may use 'nl_question' instead of 'question'."""
    raw = {"nl_question": "Count products", "sql": "SELECT COUNT(*) FROM p", "database_id": "db"}
    result = SyntheticAdapter().adapt(raw)
    assert result["question"] == "Count products"


def test_synthetic_sql_ground_truth_fallback():
    """Synthetic records may use 'ground_truth_sql' instead of 'sql'."""
    raw = {"question": "q", "ground_truth_sql": "SELECT 1;", "database_id": "db"}
    result = SyntheticAdapter().adapt(raw)
    assert result["query"] == "SELECT 1;"


def test_synthetic_db_id_fallback():
    """Synthetic records may use 'db_id' instead of 'database_id'."""
    raw = {"question": "q", "sql": "s", "db_id": "my_db"}
    result = SyntheticAdapter().adapt(raw)
    assert result["db_id"] == "my_db"


def test_synthetic_default_db_id():
    """Falls back to literal 'synthetic' when no database identifier present."""
    raw = {"question": "q", "sql": "s"}
    result = SyntheticAdapter().adapt(raw)
    assert result["db_id"] == "synthetic"


def test_synthetic_default_dialect_duckdb():
    raw = {"question": "q", "sql": "s", "database_id": "db"}
    result = SyntheticAdapter().adapt(raw)
    assert result["dialect"] == "duckdb"


def test_synthetic_default_domain():
    raw = {"question": "q", "sql": "s", "database_id": "db"}
    result = SyntheticAdapter().adapt(raw)
    assert result["domain"] == "general"


def test_synthetic_source_constant():
    assert SyntheticAdapter.SOURCE == "synthetic"
