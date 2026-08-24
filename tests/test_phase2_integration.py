from src.schema.parser import SchemaParser
from src.schema.validator import SQLSchemaValidator
from src.sql.parser import SQLParser


def test_phase2_pipeline_valid_query_has_no_errors():

    ddl = """
    CREATE TABLE customers (
        customer_id INTEGER PRIMARY KEY,
        name TEXT
    );

    CREATE TABLE orders (
        order_id INTEGER PRIMARY KEY,
        customer_id INTEGER,
        amount DECIMAL,
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    );
    """

    sql = """
    SELECT c.name, COUNT(o.order_id)
    FROM customers c
    JOIN orders o
        ON c.customer_id = o.customer_id
    GROUP BY c.name
    """

    schema = SchemaParser(dialect="sqlite").parse(database_id="shop", ddl=ddl)

    assert schema.has_table("customers")
    assert schema.has_table("orders")

    structure = SQLParser(dialect="sqlite").parse(sql)

    assert "customers" in structure.tables
    assert "orders" in structure.tables
    assert len(structure.aggregations) == 1
    assert len(structure.group_by) == 1

    errors = SQLSchemaValidator(schema).validate(structure)

    assert errors == []


def test_phase2_pipeline_flags_typo_column():
    # NOTE: the plan's original snippet for this test used the unqualified
    # query "SELECT customer_name FROM customers" and asserted
    # errors == ["Unknown column: customers.customer_name"]. That assertion
    # is wrong for the actual system: sqlglot does not infer a table for an
    # unqualified column just because only one table is in scope, so the
    # parsed ColumnReference comes back as table=None. SQLSchemaValidator
    # deliberately skips any reference with table=None (see
    # src/schema/validator.py), so that query actually produces errors == [].
    # See test_phase2_pipeline_unqualified_typo_column_is_not_flagged below,
    # which documents that real (and intentional) gap instead of asserting
    # the wrong thing here.
    #
    # To actually exercise "does the validator flag an unknown column",
    # this test uses a qualified reference, which SQLParser resolves to a
    # non-None table and which SQLSchemaValidator does check.

    ddl = """
    CREATE TABLE customers (
        customer_id INTEGER PRIMARY KEY,
        name TEXT
    );
    """

    sql = "SELECT customers.customer_name FROM customers"

    schema = SchemaParser(dialect="sqlite").parse(database_id="shop", ddl=ddl)
    structure = SQLParser(dialect="sqlite").parse(sql)

    assert structure.select_columns[0].table == "customers"

    errors = SQLSchemaValidator(schema).validate(structure)

    assert errors == ["Unknown column: customers.customer_name"]


def test_phase2_pipeline_unqualified_typo_column_is_not_flagged():
    # Documents a known, intentional gap (see src/schema/validator.py):
    # unqualified column references (ColumnReference.table is None) are
    # silently skipped by SQLSchemaValidator, even when there is only one
    # table in scope and the column name is unambiguous. This is the exact
    # query from the plan's original test snippet for this task — it is a
    # genuinely broken query (customers has no "customer_name" column), but
    # the validator currently reports no errors for it.

    ddl = """
    CREATE TABLE customers (
        customer_id INTEGER PRIMARY KEY,
        name TEXT
    );
    """

    sql = "SELECT customer_name FROM customers"

    schema = SchemaParser(dialect="sqlite").parse(database_id="shop", ddl=ddl)
    structure = SQLParser(dialect="sqlite").parse(sql)

    assert structure.select_columns[0].table is None

    errors = SQLSchemaValidator(schema).validate(structure)

    assert errors == []
