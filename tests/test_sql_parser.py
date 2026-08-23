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


from src.sql.parser import SQLParser


def test_extract_tables():

    sql = """
    SELECT *
    FROM customers c
    JOIN orders o
        ON c.customer_id = o.customer_id
    """

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert result.tables == ["customers", "orders"]


def test_extract_tables_deduplicates():

    sql = """
    SELECT *
    FROM customers c1
    JOIN customers c2
        ON c1.customer_id = c2.customer_id
    """

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert result.tables == ["customers"]


def test_extract_columns():

    sql = """
    SELECT c.name, o.order_id
    FROM customers c
    JOIN orders o
        ON c.customer_id = o.customer_id
    """

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert len(result.select_columns) == 4
    assert ColumnReference(table="c", column="name") in result.select_columns
    assert ColumnReference(table="o", column="order_id") in result.select_columns
    assert ColumnReference(table="c", column="customer_id") in result.select_columns
    assert ColumnReference(table="o", column="customer_id") in result.select_columns
