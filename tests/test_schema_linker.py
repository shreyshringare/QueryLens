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


def test_select_prunes_to_top_k_columns_and_their_tables():

    schema = _ecommerce_schema()

    pruned = _LINKER.select(
        "Which customers have spent more than 500 dollars?",
        schema,
        top_k=5,
    )

    table_names = {table.name for table in pruned.tables}
    assert table_names == {"customers", "orders", "products"}

    orders_table = pruned.get_table("orders")
    assert {column.name for column in orders_table.columns} == {"customer_id", "order_id"}

    products_table = pruned.get_table("products")
    assert {column.name for column in products_table.columns} == {"price", "product_id"}


def test_select_includes_primary_key_even_when_not_top_ranked():

    schema = _ecommerce_schema()

    pruned = _LINKER.select(
        "How many orders has each customer placed?",
        schema,
        top_k=1,
    )

    assert {table.name for table in pruned.tables} == {"orders"}

    orders_table = pruned.get_table("orders")
    assert {column.name for column in orders_table.columns} == {"customer_id", "order_id"}


def test_select_includes_all_foreign_keys_on_multi_fk_table():

    schema = _ecommerce_schema()

    pruned = _LINKER.select(
        "Which customers have spent more than 500 dollars?",
        schema,
        top_k=10,
    )

    assert {table.name for table in pruned.tables} == {"customers", "order_items", "orders", "products"}

    order_items_table = pruned.get_table("order_items")
    assert {column.name for column in order_items_table.columns} == {"order_id", "product_id", "quantity"}

    order_items_fks = {(fk.column, fk.referenced_table) for fk in order_items_table.foreign_keys}
    assert order_items_fks == {("order_id", "orders"), ("product_id", "products")}


def test_agents_package_exports():
    from src.agents import ColumnScore, SchemaLinker  # noqa: F401


from src.agents.evaluation import recall_at_k


def _users_schema() -> DatabaseSchema:

    users = Table(
        name="users",
        columns=[
            Column(name="email", data_type="TEXT"),
            Column(name="age", data_type="INT"),
        ],
    )

    return DatabaseSchema(database_id="demo", tables=[users])


def test_recall_at_k_computes_fraction_of_fully_covered_cases():

    schema = _users_schema()
    question = "What is the user's email address?"

    cases = [
        (schema, question, [("users", "email")]),  # hits @ top_k=1
        (schema, question, [("users", "age")]),     # misses @ top_k=1
    ]

    fraction = recall_at_k(cases, _LINKER, top_k=1)

    assert fraction == 0.5


def test_recall_at_3_on_real_structured_dataset_records():

    schema = _ecommerce_schema()

    cases = [
        (
            schema,
            "Which customers are from India?",
            [("customers", "customer_id"), ("customers", "name"), ("customers", "country")],
        ),
        (
            schema,
            "What is the average product price?",
            [("products", "price")],
        ),
        (
            schema,
            "Which products cost more than 100 dollars?",
            [("products", "name"), ("products", "price")],
        ),
        (
            schema,
            "How many orders has each customer placed?",
            [("orders", "customer_id")],
        ),
        (
            schema,
            "Which customers have spent more than 500 dollars?",
            [
                ("orders", "customer_id"),
                ("orders", "order_id"),
                ("order_items", "order_id"),
                ("order_items", "product_id"),
                ("products", "product_id"),
                ("order_items", "quantity"),
                ("products", "price"),
            ],
        ),
        (
            schema,
            "Which products have never been ordered?",
            [("products", "product_id"), ("products", "name"), ("order_items", "product_id")],
        ),
    ]

    fraction = recall_at_k(cases, _LINKER, top_k=3)

    # Measured, not asserted-to-be-80%: 3 of 6 real records have all their
    # ground-truth columns inside the top-3 ranked columns (records 0, 1, 3
    # hit; records 2, 4, 5 miss — record 4 in particular needs 7 ground-truth
    # columns across 3 tables, impossible to fully cover at top_k=3). This is
    # expected for a zero-shot, untrained model on 6 records — see the Task 7
    # docstring-equivalent note in the plan for why this isn't the CLAUDE.md
    # gate being claimed as met.
    assert fraction == 3 / 6
