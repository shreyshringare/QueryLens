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
