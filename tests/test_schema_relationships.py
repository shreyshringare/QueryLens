from src.schema.models import (
    Column,
    ForeignKey,
    Table,
    DatabaseSchema,
)

from src.schema.relationship_graph import extract_relationships


def test_extract_relationships():

    customer_id = Column(
        name="customer_id",
        data_type="INTEGER",
        nullable=False,
        primary_key=True,
    )

    order_customer_id = Column(
        name="customer_id",
        data_type="INTEGER",
        nullable=False,
        primary_key=False,
    )

    customers = Table(
        name="customers",
        columns=[customer_id],
        foreign_keys=[],
    )

    orders = Table(
        name="orders",
        columns=[order_customer_id],
        foreign_keys=[
            ForeignKey(
                column="customer_id",
                referenced_table="customers",
                referenced_column="customer_id",
            )
        ],
    )

    schema = DatabaseSchema(
        database_id="shop",
        tables=[
            customers,
            orders,
        ],
    )

    relationships = extract_relationships(schema)

    assert len(relationships) == 1

    relationship = relationships[0]

    assert relationship.source_table == "orders"
    assert relationship.source_column == "customer_id"
    assert relationship.target_table == "customers"
    assert relationship.target_column == "customer_id"