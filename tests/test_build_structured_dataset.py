from scripts.build_structured_dataset import transform_record


def test_transform_record():

    record = {
        "id": "0",
        "source": "synthetic",
        "domain": "general",
        "dialect": "sqlite",
        "database_id": "shop",
        "nl_question": "How many customers are there?",
        "ground_truth_sql": "SELECT COUNT(*) FROM customers",
        "ddl": "CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, name TEXT);",
        "metadata": {},
    }

    output = transform_record(record)

    assert output["id"] == "0"
    assert output["nl_question"] == "How many customers are there?"

    assert output["schema"]["database_id"] == "shop"
    assert output["schema"]["tables"][0]["name"] == "customers"

    assert output["sql_structure"]["tables"] == ["customers"]
    assert output["sql_structure"]["aggregations"][0]["function"] == "COUNT"


def test_transform_record_includes_validation_errors_key():

    record = {
        "id": "0",
        "source": "synthetic",
        "domain": "general",
        "dialect": "sqlite",
        "database_id": "shop",
        "nl_question": "How many customers are there?",
        "ground_truth_sql": "SELECT COUNT(*) FROM customers",
        "ddl": "CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, name TEXT);",
        "metadata": {},
    }

    output = transform_record(record)

    assert output["validation_errors"] == []


def test_transform_record_flags_schema_sql_mismatch():

    record = {
        "id": "1",
        "source": "synthetic",
        "domain": "general",
        "dialect": "sqlite",
        "database_id": "shop",
        "nl_question": "List all orders",
        "ground_truth_sql": "SELECT * FROM orders",
        "ddl": "CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, name TEXT);",
        "metadata": {},
    }

    output = transform_record(record)

    assert output["validation_errors"] == ["Unknown table: orders"]


def test_transform_record_flags_unknown_qualified_column():

    record = {
        "id": "2",
        "source": "synthetic",
        "domain": "general",
        "dialect": "sqlite",
        "database_id": "shop",
        "nl_question": "List customer names",
        "ground_truth_sql": "SELECT customers.naame FROM customers",
        "ddl": "CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, name TEXT);",
        "metadata": {},
    }

    output = transform_record(record)

    assert output["validation_errors"] == ["Unknown column: customers.naame"]
