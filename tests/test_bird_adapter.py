"""Tests for BIRDAdapter."""
from src.data_pipeline.adapters import BIRDAdapter


def test_bird_adapt_question_field():
    raw = {
        "question": "List all accounts",
        "SQL": "SELECT * FROM accounts;",
        "db_id": "fin_db",
        "ddl": "CREATE TABLE accounts (id INT);",
    }
    result = BIRDAdapter().adapt(raw)
    assert result["question"] == "List all accounts"
    assert result["query"] == "SELECT * FROM accounts;"
    assert result["db_id"] == "fin_db"


def test_bird_adapt_prompt_fallback():
    """BIRD sometimes uses 'prompt' instead of 'question'."""
    raw = {"prompt": "Show all users", "SQL": "SELECT * FROM users;", "db_id": "db"}
    result = BIRDAdapter().adapt(raw)
    assert result["question"] == "Show all users"


def test_bird_adapt_sql_field_fallback():
    """BIRD uses 'SQL' key; fall back to 'sql' then 'query'."""
    raw = {"question": "q", "sql": "SELECT 1;", "db_id": "db"}
    result = BIRDAdapter().adapt(raw)
    assert result["query"] == "SELECT 1;"

    raw2 = {"question": "q", "query": "SELECT 2;", "db_id": "db"}
    result2 = BIRDAdapter().adapt(raw2)
    assert result2["query"] == "SELECT 2;"


def test_bird_adapt_db_id_fallback():
    """BIRD sometimes uses 'database_id' instead of 'db_id'."""
    raw = {"question": "q", "SQL": "s", "database_id": "alt_db"}
    result = BIRDAdapter().adapt(raw)
    assert result["db_id"] == "alt_db"


def test_bird_default_dialect_mysql():
    raw = {"question": "q", "SQL": "s", "db_id": "db"}
    result = BIRDAdapter().adapt(raw)
    assert result["dialect"] == "mysql"


def test_bird_explicit_dialect_preserved():
    raw = {"question": "q", "SQL": "s", "db_id": "db", "dialect": "postgresql"}
    result = BIRDAdapter().adapt(raw)
    assert result["dialect"] == "postgresql"


def test_bird_default_domain():
    raw = {"question": "q", "SQL": "s", "db_id": "db"}
    result = BIRDAdapter().adapt(raw)
    assert result["domain"] == "general"


def test_bird_source_constant():
    assert BIRDAdapter.SOURCE == "bird"
