from src.schema.models import (
    Column,
    Table,
    DatabaseSchema,
)

from src.schema.serializer import (
    schema_to_dict,
    schema_to_json,
)


def test_schema_to_dict():

    customer_id = Column(
        name="customer_id",
        data_type="INTEGER",
        nullable=True,
        primary_key=True,
    )

    customers = Table(
        name="customers",
        columns=[customer_id],
        foreign_keys=[],
    )

    schema = DatabaseSchema(
        database_id="shop",
        tables=[customers],
    )

    result = schema_to_dict(schema)

    assert result == {
        "database_id": "shop",
        "tables": [
            {
                "name": "customers",
                "columns": [
                    {
                        "name": "customer_id",
                        "data_type": "INTEGER",
                        "nullable": True,
                        "primary_key": True,
                    }
                ],
                "foreign_keys": [],
            }
        ],
    }


def test_schema_to_json():

    customer_id = Column(
        name="customer_id",
        data_type="INTEGER",
        nullable=True,
        primary_key=True,
    )

    customers = Table(
        name="customers",
        columns=[customer_id],
        foreign_keys=[],
    )

    schema = DatabaseSchema(
        database_id="shop",
        tables=[customers],
    )

    result = schema_to_json(schema)

    assert '"database_id": "shop"' in result
    assert '"shop"' in result
    assert '"customers"' in result
    assert '"customer_id"' in result
    assert '"INTEGER"' in result