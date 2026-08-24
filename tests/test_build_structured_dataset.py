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
