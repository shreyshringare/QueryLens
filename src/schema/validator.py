from .models import DatabaseSchema
from src.sql.models import SQLStructure, ColumnReference

class SchemaValidator:

    def validate(
        self,schema: DatabaseSchema)->list[str]:

        errors = []

        table_names = set()

        for table in schema.tables:

            normalized_name = table.name.lower()

            if normalized_name in table_names:
                errors.append(
                    f"Duplicate table name found: '{table.name}'"
                )

            table_names.add(normalized_name)

            column_name = set()

            for column in table.columns:

                normalized_column_name = column.name.lower()

                if normalized_column_name in column_name:
                    errors.append(
                        f"Duplicate column name '{column.name}' found in table '{table.name}'"
                    )

                column_name.add(normalized_column_name)

        return errors


class SQLSchemaValidator:

    def __init__(self, schema: DatabaseSchema):
        self.schema = schema

    def _check_column(self, reference: ColumnReference, cte_names: set[str], errors: list[str]) -> None:

        # Unqualified columns (table=None) are not validated here: without
        # a table name we cannot know which table's column set to check
        # against, so they are silently skipped rather than flagged.
        if reference.table is None:
            return

        # A column qualified by a CTE name (e.g. "recent.customer_id")
        # refers to a query-local result set, not a real schema table,
        # so it can't be checked against DatabaseSchema and is skipped
        # rather than reported as an unknown column.
        if reference.table.lower() in cte_names:
            return

        if not self.schema.has_column(reference.table, reference.column):
            errors.append(
                f"Unknown column: {reference.table}.{reference.column}"
            )

    def validate(self, sql_structure: SQLStructure) -> list[str]:

        errors = []

        cte_names = {name.lower() for name in sql_structure.cte_names}

        for table_name in sql_structure.tables:

            if not self.schema.has_table(table_name):
                errors.append(f"Unknown table: {table_name}")

        for reference in sql_structure.select_columns:
            self._check_column(reference, cte_names, errors)

        return errors
