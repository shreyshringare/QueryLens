from src.schema.models import (
    Column,
    Table,
    DatabaseSchema,
)

from src.schema.serializer import (
    schema_to_dict,
    schema_to_json,
)

from src.schema.validator import SQLSchemaValidator
from src.sql.models import SQLStructure, ColumnReference


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


def _build_shop_schema():

    customer_id = Column(name="customer_id", data_type="INTEGER", primary_key=True)
    name_col = Column(name="name", data_type="TEXT")

    customers = Table(name="customers", columns=[customer_id, name_col])

    return DatabaseSchema(database_id="shop", tables=[customers])


def test_sql_schema_validator_passes_for_known_references():

    schema = _build_shop_schema()

    structure = SQLStructure(
        tables=["customers"],
        select_columns=[ColumnReference(table="customers", column="name")],
    )

    validator = SQLSchemaValidator(schema)

    errors = validator.validate(structure)

    assert errors == []


def test_sql_schema_validator_flags_unknown_table():

    schema = _build_shop_schema()

    structure = SQLStructure(tables=["orders"])

    validator = SQLSchemaValidator(schema)

    errors = validator.validate(structure)

    assert errors == ["Unknown table: orders"]


def test_sql_schema_validator_flags_unknown_column():

    schema = _build_shop_schema()

    structure = SQLStructure(
        tables=["customers"],
        select_columns=[ColumnReference(table="customers", column="customer_name")],
    )

    validator = SQLSchemaValidator(schema)

    errors = validator.validate(structure)

    assert errors == ["Unknown column: customers.customer_name"]


def test_sql_schema_validator_column_lookup_is_case_insensitive():

    schema = _build_shop_schema()

    structure = SQLStructure(
        tables=["customers"],
        select_columns=[ColumnReference(table="customers", column="NAME")],
    )

    validator = SQLSchemaValidator(schema)

    errors = validator.validate(structure)

    assert errors == []