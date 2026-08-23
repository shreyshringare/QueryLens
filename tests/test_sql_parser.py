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


def test_extract_joins():

    sql = """
    SELECT *
    FROM customers c
    JOIN orders o
        ON c.customer_id = o.customer_id
    """

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert len(result.joins) == 1

    join = result.joins[0]

    assert join.table == "orders"
    assert join.join_type == "JOIN"
    assert join.left == ColumnReference(table="c", column="customer_id")
    assert join.right == ColumnReference(table="o", column="customer_id")


def test_extract_joins_left_join_type():

    sql = """
    SELECT *
    FROM customers c
    LEFT JOIN orders o
        ON c.customer_id = o.customer_id
    """

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert len(result.joins) == 1
    assert result.joins[0].join_type == "LEFT"


def test_extract_filters():

    sql = """
    SELECT *
    FROM orders o
    WHERE o.amount > 1000
      AND o.status = 'shipped'
    """

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert len(result.filters) == 2

    operators = {f.operator for f in result.filters}
    assert operators == {"GT", "EQ"}

    amount_filter = next(f for f in result.filters if f.operator == "GT")
    assert amount_filter.column == ColumnReference(table="o", column="amount")


def test_extract_filters_like_predicate():

    sql = """
    SELECT *
    FROM customers c
    WHERE c.name LIKE 'A%'
    """

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert len(result.filters) == 1
    assert result.filters[0].operator == "LIKE"
    assert result.filters[0].column == ColumnReference(table="c", column="name")


def test_extract_filters_no_where_clause():

    sql = """
    SELECT *
    FROM customers c
    """

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert result.filters == []


def test_extract_filters_bare_column_no_spurious_filter():

    sql = """
    SELECT *
    FROM customers c
    WHERE c.is_active
    """

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert result.filters == []


def test_extract_filters_negated_predicate_not_inverted():

    sql = "SELECT * FROM customers c WHERE c.email IS NOT NULL"

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert len(result.filters) == 1
    assert result.filters[0].operator == "NOT IS"
    assert "NOT" in result.filters[0].value


def test_extract_aggregations():

    sql = "SELECT COUNT(o.order_id), SUM(o.amount) FROM orders o"

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert len(result.aggregations) == 2

    functions = {a.function for a in result.aggregations}
    assert functions == {"COUNT", "SUM"}

    count_agg = next(a for a in result.aggregations if a.function == "COUNT")
    assert count_agg.column == ColumnReference(table="o", column="order_id")


def test_extract_aggregations_count_star():

    sql = "SELECT COUNT(*) FROM orders o"

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert len(result.aggregations) == 1
    assert result.aggregations[0].function == "COUNT"
    assert result.aggregations[0].column is None


def test_extract_aggregations_window_function_included():

    sql = "SELECT SUM(o.amount) OVER (PARTITION BY o.customer_id) FROM orders o"

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert len(result.aggregations) == 1
    assert result.aggregations[0].function == "SUM"
    assert result.aggregations[0].column == ColumnReference(table="o", column="amount")


def test_extract_group_by():

    sql = "SELECT c.name, COUNT(*) FROM customers c GROUP BY c.name"

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert result.group_by == [ColumnReference(table="c", column="name")]


def test_extract_group_by_absent():

    sql = "SELECT * FROM orders o"

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert result.group_by == []


def test_extract_group_by_multiple_columns():

    sql = "SELECT c.name, c.email, COUNT(*) FROM customers c GROUP BY c.name, c.email"

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert result.group_by == [
        ColumnReference(table="c", column="name"),
        ColumnReference(table="c", column="email"),
    ]
