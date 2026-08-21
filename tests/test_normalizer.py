from src.data_pipeline.normalizer import QueryNormalizer


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

    assert (
        result.ground_truth_sql
        == "SELECT COUNT(*) FROM users"
    )