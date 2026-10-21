import pytest

from src.dialect.models import AdaptResult
from src.dialect.adapter import DialectAdapter


def test_adapt_result_holds_values():

    result = AdaptResult(
        sql="SELECT 1",
        success=True,
        error=None,
        source_dialect="postgresql",
        target_dialect="mysql",
    )

    assert result.sql == "SELECT 1"
    assert result.success is True
    assert result.error is None
    assert result.source_dialect == "postgresql"
    assert result.target_dialect == "mysql"


def test_adapt_rejects_unknown_source_dialect():

    adapter = DialectAdapter()

    result = adapter.adapt("SELECT 1", source_dialect="oracle", target_dialect="postgresql")

    assert result.success is False
    assert result.sql is None
    assert "oracle" in result.error
    assert result.source_dialect == "oracle"
    assert result.target_dialect == "postgresql"


def test_adapt_rejects_unknown_target_dialect():

    adapter = DialectAdapter()

    result = adapter.adapt("SELECT 1", source_dialect="postgresql", target_dialect="unknown")

    assert result.success is False
    assert result.sql is None
    assert "unknown" in result.error


def test_adapt_transpiles_concat_postgresql_to_mysql():

    adapter = DialectAdapter()

    result = adapter.adapt(
        "SELECT a || b FROM t",
        source_dialect="postgresql",
        target_dialect="mysql",
    )

    assert result.success is True
    assert result.error is None
    assert result.sql == "SELECT CONCAT(a, b) FROM t"


def test_adapt_catches_invalid_sql():

    adapter = DialectAdapter()

    result = adapter.adapt(
        "SELECT FROM FROM",
        source_dialect="sqlite",
        target_dialect="postgresql",
    )

    assert result.success is False
    assert result.sql is None
    assert result.error is not None
    assert len(result.error) > 0


def test_adapt_same_dialect_round_trip():

    adapter = DialectAdapter()

    result = adapter.adapt(
        "select a,b from t where a>1",
        source_dialect="duckdb",
        target_dialect="duckdb",
    )

    assert result.success is True
    assert result.sql == "SELECT a, b FROM t WHERE a > 1"


def test_dialect_package_exports():
    from src.dialect import AdaptResult, DialectAdapter  # noqa: F401


CROSS_DIALECT_CASES = [
    # (sql, source_dialect, target_dialect, expected_sql)
    ("SELECT a || b FROM t", "postgresql", "mysql", "SELECT CONCAT(a, b) FROM t"),
    ("SELECT a || b FROM t", "sqlite", "mysql", "SELECT CONCAT(a, b) FROM t"),
    ("SELECT a || b FROM t", "duckdb", "postgresql", "SELECT a || b FROM t"),
    ("SELECT a || b FROM t", "sqlite", "duckdb", "SELECT a || b FROM t"),

    ("SELECT GROUP_CONCAT(name) FROM t", "postgresql", "mysql", "SELECT GROUP_CONCAT(name SEPARATOR ',') FROM t"),
    ("SELECT GROUP_CONCAT(name) FROM t", "postgresql", "duckdb", "SELECT LISTAGG(name, ',') FROM t"),
    ("SELECT GROUP_CONCAT(name) FROM t", "mysql", "postgresql", "SELECT STRING_AGG(name, ',') FROM t"),
    ("SELECT GROUP_CONCAT(name) FROM t", "duckdb", "sqlite", "SELECT GROUP_CONCAT(name) FROM t"),

    ("SELECT IFNULL(a, 0) FROM t", "postgresql", "mysql", "SELECT COALESCE(a, 0) FROM t"),
    ("SELECT IFNULL(a, 0) FROM t", "sqlite", "duckdb", "SELECT COALESCE(a, 0) FROM t"),
    ("SELECT IFNULL(a, 0) FROM t", "mysql", "sqlite", "SELECT COALESCE(a, 0) FROM t"),

    ("SELECT * FROM t LIMIT 5, 10", "mysql", "postgresql", "SELECT * FROM t LIMIT 10 OFFSET 5"),
    ("SELECT * FROM t LIMIT 5, 10", "mysql", "sqlite", "SELECT * FROM t LIMIT 10 OFFSET 5"),
    ("SELECT * FROM t LIMIT 10 OFFSET 5", "postgresql", "duckdb", "SELECT * FROM t LIMIT 10 OFFSET 5"),

    ("SELECT CAST(a AS INTEGER) FROM t", "postgresql", "mysql", "SELECT CAST(a AS SIGNED) FROM t"),
    ("SELECT CAST(a AS INTEGER) FROM t", "mysql", "postgresql", "SELECT CAST(a AS INT) FROM t"),
    ("SELECT CAST(a AS TEXT) FROM t", "sqlite", "mysql", "SELECT CAST(a AS CHAR) FROM t"),
    ("SELECT CAST(a AS TEXT) FROM t", "mysql", "postgresql", "SELECT CAST(a AS TEXT) FROM t"),

    ("SELECT TRUE, FALSE", "postgresql", "mysql", "SELECT TRUE, FALSE"),

    ("SELECT SUBSTR(a, 1, 3) FROM t", "mysql", "postgresql", "SELECT SUBSTRING(a FROM 1 FOR 3) FROM t"),
    ("SELECT SUBSTR(a, 1, 3) FROM t", "postgresql", "mysql", "SELECT SUBSTRING(a, 1, 3) FROM t"),

    ("SELECT IF(a > 1, 'x', 'y') FROM t", "postgresql", "sqlite", "SELECT IIF(a > 1, 'x', 'y') FROM t"),
    ("SELECT IF(a > 1, 'x', 'y') FROM t", "mysql", "duckdb", "SELECT CASE WHEN a > 1 THEN 'x' ELSE 'y' END FROM t"),
]


@pytest.mark.parametrize("sql,source,target,expected", CROSS_DIALECT_CASES)
def test_cross_dialect_transpile(sql, source, target, expected):

    adapter = DialectAdapter()

    result = adapter.adapt(sql, source_dialect=source, target_dialect=target)

    assert result.success is True
    assert result.error is None
    assert result.sql == expected
