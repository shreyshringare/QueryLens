from src.dialect.adapter import DialectAdapter


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
