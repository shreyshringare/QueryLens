from src.dialect.models import AdaptResult


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
