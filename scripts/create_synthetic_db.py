import duckdb
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

BASE = ROOT / "data" / "raw" / "synthetic" / "ecommerce"

SCHEMA_FILE = BASE / "schema.sql"
DB_FILE = BASE / "database.duckdb"


def main():
    BASE.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(str(DB_FILE))

    schema_sql = SCHEMA_FILE.read_text()

    conn.execute(schema_sql)

    conn.execute("""
        INSERT INTO customers VALUES
        (1, 'Alice', 'India'),
        (2, 'Bob', 'USA'),
        (3, 'Charlie', 'India'),
        (4, 'David', 'UK'),
        (5, 'Eva', 'USA');
    """)

    conn.execute("""
        INSERT INTO products VALUES
        (1, 'Laptop', 'Electronics', 1000),
        (2, 'Mouse', 'Electronics', 25),
        (3, 'Keyboard', 'Electronics', 75),
        (4, 'Chair', 'Furniture', 200),
        (5, 'Desk', 'Furniture', 500);
    """)

    conn.execute("""
        INSERT INTO orders VALUES
        (101, 1, '2025-01-10'),
        (102, 1, '2025-02-10'),
        (103, 2, '2025-03-10'),
        (104, 3, '2025-04-10'),
        (105, 3, '2025-05-10');
    """)

    conn.execute("""
        INSERT INTO order_items VALUES
        (101, 1, 1),
        (101, 2, 2),
        (102, 3, 1),
        (103, 4, 2),
        (104, 5, 1),
        (105, 1, 1);
    """)

    conn.close()

    print(f"Created: {DB_FILE}")


if __name__ == "__main__":
    main()