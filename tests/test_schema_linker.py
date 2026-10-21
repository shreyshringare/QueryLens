from sentence_transformers import CrossEncoder

from src.agents.schema_linker import ColumnScore, SchemaLinker


def test_column_score_holds_values():

    score = ColumnScore(table="customers", column="name", score=-1.5)

    assert score.table == "customers"
    assert score.column == "name"
    assert score.score == -1.5


def test_schema_linker_loads_default_model():

    linker = SchemaLinker()

    assert isinstance(linker.model, CrossEncoder)


from src.schema.models import Column, DatabaseSchema, ForeignKey, Table


def _ecommerce_schema() -> DatabaseSchema:

    customers = Table(
        name="customers",
        columns=[
            Column(name="customer_id", data_type="INT", primary_key=True),
            Column(name="name", data_type="TEXT"),
            Column(name="country", data_type="TEXT"),
        ],
    )
    products = Table(
        name="products",
        columns=[
            Column(name="product_id", data_type="INT", primary_key=True),
            Column(name="name", data_type="TEXT"),
            Column(name="category", data_type="TEXT"),
            Column(name="price", data_type="DOUBLE"),
        ],
    )
    orders = Table(
        name="orders",
        columns=[
            Column(name="order_id", data_type="INT", primary_key=True),
            Column(name="customer_id", data_type="INT"),
            Column(name="order_date", data_type="DATE"),
        ],
        foreign_keys=[
            ForeignKey(column="customer_id", referenced_table="customers", referenced_column="customer_id"),
        ],
    )
    order_items = Table(
        name="order_items",
        columns=[
            Column(name="order_id", data_type="INT"),
            Column(name="product_id", data_type="INT"),
            Column(name="quantity", data_type="INT"),
        ],
        foreign_keys=[
            ForeignKey(column="order_id", referenced_table="orders", referenced_column="order_id"),
            ForeignKey(column="product_id", referenced_table="products", referenced_column="product_id"),
        ],
    )

    return DatabaseSchema(
        database_id="ecommerce",
        tables=[customers, products, orders, order_items],
    )


# Model loaded once at module scope — the ~1-3s load cost is paid once for the
# whole test file, not once per test.
_LINKER = SchemaLinker()


def test_rank_orders_all_columns_by_relevance():

    schema = _ecommerce_schema()

    results = _LINKER.rank("Which customers are from India?", schema)

    assert len(results) == 13

    top_3 = {(r.table, r.column) for r in results[:3]}
    assert top_3 == {
        ("customers", "country"),
        ("customers", "name"),
        ("customers", "customer_id"),
    }
