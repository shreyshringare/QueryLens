from src.schema.parser import SchemaParser

def test_parse_basic_scheme():
    
    ddl= """
    CREATE TABLE customers (
        customer_id INTEGER PRIMARY KEY,
        name TEXT,
        email TEXT
    );

    CREATE TABLE orders (
        order_id INTEGER PRIMARY KEY,
        customer_id INTEGER,
        amount DECIMAL
    );
    """
    
    parser = SchemaParser(dialect="sqlite")
    
    schema = parser.parse(database_id="shop",ddl=ddl,)
    
    assert schema.database_id == "shop"
    
    assert len(schema.tables) == 2
    
    customers = schema.get_table("customers")

    assert customers is not None
    
    assert customers.get_column(
        "customer_id"
    ) is not None

    assert customers.get_column(
        "customer_id"
    ).primary_key is True  


def test_parse_foreign_key_constraint():
    ddl = """
    CREATE TABLE customers (
        customer_id INTEGER PRIMARY KEY
    );

    CREATE TABLE orders (
        order_id INTEGER PRIMARY KEY,
        customer_id INTEGER,
        FOREIGN KEY (customer_id)
            REFERENCES customers(customer_id)
    );
    """

    schema = SchemaParser(dialect="sqlite").parse(
        database_id="shop",
        ddl=ddl,
    )

    orders = schema.get_table("orders")

    assert orders is not None
    assert len(orders.foreign_keys) == 1
    assert orders.foreign_keys[0].column == "customer_id"
    assert orders.foreign_keys[0].referenced_table == "customers"
    assert orders.foreign_keys[0].referenced_column == "customer_id"