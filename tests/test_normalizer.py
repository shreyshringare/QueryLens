from src.data_pipeline.adapters import BIRDAdapter, SpiderAdapter, SyntheticAdapter
from src.data_pipeline.dialects import normalize_dialect
from src.data_pipeline.normalizer import QueryNormalizer
from src.data_pipeline.pipeline import normalize_record


def test_normalize_synthetic_record():
    record = {
        "question": "How many users are there?",
        "sql": "SELECT COUNT(*) FROM users",
        "ddl": """
            CREATE TABLE users (
                id INTEGER,
                name VARCHAR
            )
        """,
        "domain": "ecommerce",
        "dialect": "duckdb",
        "database_id": "shop",
    }

    normalizer = QueryNormalizer("synthetic")
    result = normalizer.normalize(record, 0)

    assert result.source == "synthetic"
    assert result.domain == "ecommerce"
    assert result.dialect == "duckdb"
    assert result.database_id == "shop"
    assert result.nl_question == "How many users are there?"
    assert result.ground_truth_sql == "SELECT COUNT(*) FROM users"
    assert "CREATE TABLE users" in result.ddl


def test_spider_adapter_and_normalization():
    spider_raw = {
        "question": "How many singers are there?",
        "query": "SELECT COUNT(*) FROM singer",
        "db_id": "concert_singer",
        "ddl": "CREATE TABLE singer (id INT, name TEXT);",
    }

    result = normalize_record("spider", spider_raw, 1)

    assert result.source == "spider"
    assert result.dialect == "sqlite"
    assert result.database_id == "concert_singer"
    assert result.nl_question == "How many singers are there?"
    assert result.ground_truth_sql == "SELECT COUNT(*) FROM singer"
    assert result.ddl == "CREATE TABLE singer (id INT, name TEXT);"


def test_bird_adapter_dialect_mapping():
    bird_raw = {
        "prompt": "List all financial accounts",
        "SQL": "SELECT * FROM accounts;",
        "db_id": "financial_db",
        "dialect": "postgres",
        "ddl": "CREATE TABLE accounts (id INT);",
    }

    result = normalize_record("bird", bird_raw, 2)

    assert result.source == "bird"
    assert result.dialect == "postgresql"
    assert result.database_id == "financial_db"
    assert result.nl_question == "List all financial accounts"


def test_dialect_normalization_aliases():
    assert normalize_dialect("postgres") == "postgresql"
    assert normalize_dialect("pg") == "postgresql"
    assert normalize_dialect("sqlite3") == "sqlite"
    assert normalize_dialect("duckdb") == "duckdb"
    assert normalize_dialect("unknown_dialect") == "unknown"


def test_process_source_synthetic():
    from pathlib import Path

    from scripts.build_normalized_dataset import process_source
    from src.data_pipeline.quality import QualityReport

    synthetic_file = Path("data/raw/synthetic/ecommerce/examples.jsonl")
    if synthetic_file.exists():
        records = process_source("synthetic", synthetic_file, QualityReport())
        assert len(records) == 6
        assert records[0].dialect == "duckdb"
        assert records[0].database_id == "ecommerce"



def test_dataclass_serialization(tmp_path):
    import json
    from src.data_pipeline.models import NormalizedQuery, save_json, save_jsonl

    query = NormalizedQuery(
        id="1",
        source="synthetic",
        domain="general",
        dialect="duckdb",
        database_id="test_db",
        nl_question="What is the total price?",
        ground_truth_sql="SELECT SUM(price) FROM products",
        ddl="CREATE TABLE products (price DOUBLE);",
    )

    d = query.to_dict()
    assert d["id"] == "1"
    assert d["nl_question"] == "What is the total price?"

    j_str = query.to_json()
    assert '"database_id": "test_db"' in j_str

    jsonl_path = tmp_path / "test.jsonl"
    json_path = tmp_path / "test.json"

    save_jsonl([query], jsonl_path)
    assert jsonl_path.exists()
    lines = jsonl_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["id"] == "1"

    save_json([query], json_path)
    assert json_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["id"] == "1"


def test_split_records():
    from src.data_pipeline.split import split_records

    items = list(range(100))
    train, val, test = split_records(items, train_ratio=0.8, val_ratio=0.1, seed=42)

    assert len(train) == 80
    assert len(val) == 10
    assert len(test) == 10
    assert set(train).isdisjoint(set(val))
    assert set(train).isdisjoint(set(test))
    assert set(val).isdisjoint(set(test))


def test_split_records_by_database():
    from src.data_pipeline.models import NormalizedQuery
    from src.data_pipeline.split import split_records_by_database

    records = [
        NormalizedQuery("1", "synth", "gen", "duckdb", "db_A", "q1", "s1", "ddl"),
        NormalizedQuery("2", "synth", "gen", "duckdb", "db_A", "q2", "s2", "ddl"),
        NormalizedQuery("3", "synth", "gen", "duckdb", "db_B", "q3", "s3", "ddl"),
        NormalizedQuery("4", "synth", "gen", "duckdb", "db_C", "q4", "s4", "ddl"),
    ]

    train, val, test = split_records_by_database(records, seed=42)
    train_dbs = {r.database_id for r in train}
    val_dbs = {r.database_id for r in val}
    test_dbs = {r.database_id for r in test}

    assert train_dbs.isdisjoint(val_dbs)
    assert train_dbs.isdisjoint(test_dbs)
    assert val_dbs.isdisjoint(test_dbs)


def test_dataset_statistics():
    from src.data_pipeline.models import NormalizedQuery
    from src.data_pipeline.stats import dataset_statistics, format_dataset_statistics

    records = [
        NormalizedQuery("1", "spider", "finance", "sqlite", "db_1", "q1", "s1", "ddl"),
        NormalizedQuery("2", "bird", "medical", "mysql", "db_2", "q2", "s2", "ddl"),
        NormalizedQuery("3", "synthetic", "finance", "duckdb", "db_1", "q3", "s3", "ddl"),
    ]

    stats = dataset_statistics(records)
    assert stats["total"] == 3
    assert stats["sources"]["spider"] == 1
    assert stats["sources"]["bird"] == 1
    assert stats["sources"]["synthetic"] == 1
    assert stats["databases"] == 2

    formatted = format_dataset_statistics(stats)
    assert "Total records: 3" in formatted
    assert "spider: 1" in formatted
    assert "Databases:\n  2" in formatted


def test_quality_report(tmp_path):
    import json

    from src.data_pipeline.quality import QualityReport

    report = QualityReport(
        total_records=100,
        valid_records=90,
        invalid_records=10,
        duplicates_removed=5,
        missing_ddl=3,
        missing_sql=2,
        missing_question=1,
    )

    d = report.to_dict()
    assert d["total_records"] == 100
    assert d["valid_records"] == 90
    assert d["duplicates_removed"] == 5
    # error_details should be omitted when empty
    assert "error_details" not in d

    path = tmp_path / "quality_report.json"
    report.save(path)
    assert path.exists()

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["total_records"] == 100
    assert saved["missing_ddl"] == 3
    assert saved["missing_sql"] == 2
    assert saved["missing_question"] == 1




