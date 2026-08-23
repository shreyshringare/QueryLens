from src.sql.models import (
    ColumnReference,
    Join,
    Filter,
    Aggregation,
    OrderBy,
    SQLStructure,
)


def test_sql_structure_defaults():

    structure = SQLStructure()

    assert structure.select_columns == []
    assert structure.tables == []
    assert structure.joins == []
    assert structure.filters == []
    assert structure.aggregations == []
    assert structure.group_by == []
    assert structure.order_by == []
    assert structure.limit is None


def test_sql_structure_holds_values():

    ref = ColumnReference(table="customers", column="name")

    structure = SQLStructure(
        select_columns=[ref],
        tables=["customers"],
        limit=10,
    )

    assert structure.select_columns == [ref]
    assert structure.tables == ["customers"]
    assert structure.limit == 10


def test_sql_package_exports():
    from src.sql import ColumnReference, SQLStructure  # noqa: F401
