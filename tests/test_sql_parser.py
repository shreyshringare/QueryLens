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
    assert ColumnReference(table="customers", column="name") in result.select_columns
    assert ColumnReference(table="orders", column="order_id") in result.select_columns
    assert ColumnReference(table="customers", column="customer_id") in result.select_columns
    assert ColumnReference(table="orders", column="customer_id") in result.select_columns


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
    assert join.left == ColumnReference(table="customers", column="customer_id")
    assert join.right == ColumnReference(table="orders", column="customer_id")


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


def test_extract_joins_using_clause():

    sql = """
    SELECT *
    FROM customers c
    JOIN orders o
        USING (customer_id)
    """

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert len(result.joins) == 1

    join = result.joins[0]

    assert join.table == "orders"
    assert join.join_type == "JOIN"
    assert join.left == ColumnReference(table=None, column="customer_id")
    assert join.right == ColumnReference(table="orders", column="customer_id")


def test_extract_joins_using_clause_multiple_columns():

    sql = """
    SELECT *
    FROM order_items oi
    JOIN orders o
        USING (order_id, region_id)
    """

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert len(result.joins) == 2
    assert {j.left.column for j in result.joins} == {"order_id", "region_id"}
    assert all(j.table == "orders" for j in result.joins)


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
    assert amount_filter.column == ColumnReference(table="orders", column="amount")


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
    assert result.filters[0].column == ColumnReference(table="customers", column="name")


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
    assert count_agg.column == ColumnReference(table="orders", column="order_id")


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
    assert result.aggregations[0].column == ColumnReference(table="orders", column="amount")


def test_extract_group_by():

    sql = "SELECT c.name, COUNT(*) FROM customers c GROUP BY c.name"

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert result.group_by == [ColumnReference(table="customers", column="name")]


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
        ColumnReference(table="customers", column="name"),
        ColumnReference(table="customers", column="email"),
    ]


def test_extract_group_by_rollup():

    sql = "SELECT c.region, c.name, COUNT(*) FROM customers c GROUP BY ROLLUP(c.region, c.name)"

    parser = SQLParser(dialect="postgres")

    result = parser.parse(sql)

    assert result.group_by == [
        ColumnReference(table="customers", column="region"),
        ColumnReference(table="customers", column="name"),
    ]


def test_extract_group_by_cube():

    sql = "SELECT c.region, c.name, COUNT(*) FROM customers c GROUP BY CUBE(c.region, c.name)"

    parser = SQLParser(dialect="postgres")

    result = parser.parse(sql)

    assert result.group_by == [
        ColumnReference(table="customers", column="region"),
        ColumnReference(table="customers", column="name"),
    ]


def test_extract_group_by_grouping_sets():

    sql = (
        "SELECT c.region, c.name, COUNT(*) FROM customers c "
        "GROUP BY GROUPING SETS ((c.region), (c.name))"
    )

    parser = SQLParser(dialect="postgres")

    result = parser.parse(sql)

    assert result.group_by == [
        ColumnReference(table="customers", column="region"),
        ColumnReference(table="customers", column="name"),
    ]


def test_extract_order_by():

    sql = "SELECT * FROM orders o ORDER BY o.amount DESC"

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert len(result.order_by) == 1
    assert result.order_by[0].direction == "DESC"
    assert "amount" in result.order_by[0].expression


def test_extract_order_by_default_ascending():

    sql = "SELECT * FROM orders o ORDER BY o.amount"

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert len(result.order_by) == 1
    assert result.order_by[0].direction == "ASC"


def test_extract_order_by_aggregate_expression():

    sql = "SELECT COUNT(o.id) FROM orders o ORDER BY COUNT(o.id) DESC"

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert len(result.order_by) == 1
    assert result.order_by[0].direction == "DESC"
    assert result.order_by[0].expression == "COUNT(o.id)"


def test_extract_order_by_multiple_items_independent_directions():

    sql = "SELECT * FROM orders o ORDER BY o.amount, o.created_at DESC"

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert len(result.order_by) == 2
    assert result.order_by[0].direction == "ASC"
    assert "amount" in result.order_by[0].expression
    assert result.order_by[1].direction == "DESC"
    assert "created_at" in result.order_by[1].expression


def test_extract_limit():

    sql = "SELECT * FROM orders o LIMIT 10"

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert result.limit == 10


def test_extract_limit_absent():

    sql = "SELECT * FROM orders o"

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert result.limit is None


def test_extract_limit_fetch_first_syntax_not_captured():

    sql = "SELECT * FROM orders FETCH FIRST 10 ROWS ONLY"

    parser = SQLParser(dialect="oracle")

    result = parser.parse(sql)

    assert result.limit is None


from src.sql.aliases import AliasResolver


def test_alias_resolver():

    resolver = AliasResolver()
    resolver.add("c", "customers")
    resolver.add("o", "orders")

    assert resolver.resolve("c") == "customers"
    assert resolver.resolve("o") == "orders"
    assert resolver.resolve("customers") == "customers"  # unknown key -> passthrough


def test_alias_resolution_in_parse():

    sql = """
    SELECT c.name, o.order_id
    FROM customers c
    JOIN orders o
        ON c.customer_id = o.customer_id
    GROUP BY c.name
    """

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert ColumnReference(table="customers", column="name") in result.select_columns
    assert ColumnReference(table="orders", column="order_id") in result.select_columns

    join = result.joins[0]
    assert join.left == ColumnReference(table="customers", column="customer_id")
    assert join.right == ColumnReference(table="orders", column="customer_id")

    assert result.group_by == [ColumnReference(table="customers", column="name")]


def test_alias_resolution_no_alias_used():

    sql = "SELECT customers.name FROM customers"

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert ColumnReference(table="customers", column="name") in result.select_columns


def test_alias_resolution_subquery_alias_collision_known_limitation():

    sql = """
    SELECT a.id, sub.y
    FROM foo a
    JOIN (SELECT bar.y AS y, a.id AS aid FROM bar a) sub
        ON a.id = sub.aid
    """

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    # Known limitation: outer "a" (foo) gets overwritten by the subquery's
    # "a" (bar) in the flat resolver, so a.id incorrectly resolves to bar,
    # not foo. This test documents current behavior, not correct behavior —
    # if scope-aware resolution is ever added, this test should be updated
    # to assert table="foo" instead.
    id_ref = next(r for r in result.select_columns if r.column == "id")
    assert id_ref.table == "bar"


def test_extract_tables_excludes_cte_names():

    sql = """
    WITH recent AS (
        SELECT customer_id, amount FROM orders WHERE amount > 100
    )
    SELECT customer_id FROM recent
    """

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert result.tables == ["orders"]


def test_extract_tables_self_referencing_shadowed_cte():

    sql = """
    WITH orders AS (
        SELECT id, amount FROM orders WHERE amount > 100
    )
    SELECT * FROM orders
    """

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert result.tables == ["orders"]


def test_extract_tables_records_cte_names():

    sql = """
    WITH recent AS (
        SELECT customer_id, amount FROM orders WHERE amount > 100
    )
    SELECT recent.customer_id FROM recent
    """

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert result.cte_names == ["recent"]


def test_extract_tables_no_cte_names_when_absent():

    sql = "SELECT * FROM orders o"

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert result.cte_names == []
