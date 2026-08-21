"""Tests for SpiderAdapter."""
from src.data_pipeline.adapters import SpiderAdapter


def test_spider_adapt_basic():
    raw = {
        "question": "How many singers are there?",
        "query": "SELECT COUNT(*) FROM singer",
        "db_id": "concert_singer",
        "ddl": "CREATE TABLE singer (id INT, name TEXT);",
    }
    result = SpiderAdapter().adapt(raw)

    assert result["question"] == "How many singers are there?"
    assert result["query"] == "SELECT COUNT(*) FROM singer"
    assert result["db_id"] == "concert_singer"
    assert result["ddl"] == "CREATE TABLE singer (id INT, name TEXT);"
    assert result["dialect"] == "sqlite"  # always sqlite for Spider


def test_spider_dialect_always_sqlite():
    """Spider records should always map to sqlite regardless of any dialect field."""
    raw = {"question": "q", "query": "s", "db_id": "db", "dialect": "mysql"}
    result = SpiderAdapter().adapt(raw)
    assert result["dialect"] == "sqlite"


def test_spider_default_domain():
    raw = {"question": "q", "query": "s", "db_id": "db"}
    result = SpiderAdapter().adapt(raw)
    assert result["domain"] == "general"


def test_spider_metadata_preserves_db_id():
    raw = {"question": "q", "query": "s", "db_id": "my_db"}
    result = SpiderAdapter().adapt(raw)
    assert result["metadata"]["original_db_id"] == "my_db"


def test_spider_missing_fields_return_none():
    result = SpiderAdapter().adapt({})
    assert result["question"] is None
    assert result["query"] is None
    assert result["db_id"] is None
    assert result["ddl"] is None


def test_spider_source_constant():
    assert SpiderAdapter.SOURCE == "spider"
