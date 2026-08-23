import sqlglot

from .models import (
    Column,
    ForeignKey,
    Table,
    DatabaseSchema,
)


class SchemaParser:
    def __init__(self, dialect: str | None = None):
        self.dialect = dialect

    def parse(
        self,
        database_id: str,
        ddl: str,
    ) -> DatabaseSchema:

        statements = sqlglot.parse(
            ddl,
            read=self.dialect,
        )

        tables = []

        for statement in statements:
            table = self._parse_create_table(statement)

            if table is not None:
                tables.append(table)

        return DatabaseSchema(
            database_id=database_id,
            tables=tables,
        )

    def _parse_create_table(self, statement):

        if not isinstance(
            statement,
            sqlglot.expressions.Create
        ):
            return None

        schema = statement.this

        if not isinstance(
            schema,
            sqlglot.expressions.Schema
        ):
            return None

        table_name = schema.this.name

        columns = []
        foreign_keys = []

        for expression in schema.expressions:

            if isinstance(
                expression,
                sqlglot.expressions.ColumnDef
            ):
                column = self._parse_column(
                    expression
                )

                columns.append(column)

            elif isinstance(
                expression,
                (
                    sqlglot.expressions.Constraint,
                    sqlglot.expressions.ForeignKey,
                ),
            ):
                self._parse_constraint(
                    expression,
                    foreign_keys,
                    columns,
                )

        return Table(
            name=table_name,
            columns=columns,
            foreign_keys=foreign_keys,
        )

    def _parse_column(self, expression):

        name = expression.this.name

        data_type = str(
            expression.args.get("kind")
        )

        constraints = expression.args.get(
            "constraints",
            []
        )

        primary_key = False
        nullable = True

        for constraint in constraints:

            kind = constraint.kind

            if isinstance(
                kind,
                sqlglot.expressions.PrimaryKeyColumnConstraint,
            ):
                primary_key = True

            if isinstance(
                kind,
                sqlglot.expressions.NotNullColumnConstraint,
            ):
                nullable = False

        return Column(
            name=name,
            data_type=data_type,
            nullable=nullable,
            primary_key=primary_key,
        )

    def _parse_constraint(
        self,
        expression,
        foreign_keys,
        columns,
    ):
        constraints = (
            expression.expressions
            if isinstance(
                expression,
                sqlglot.expressions.Constraint,
            )
            else [expression]
        )

        for constraint in constraints:

            if not isinstance(
                constraint,
                sqlglot.expressions.ForeignKey,
            ):
                continue

            reference = constraint.args.get("reference")

            if reference is None:
                continue

            referenced_schema = reference.this
            referenced_table = referenced_schema.this.name
            referenced_columns = [
                column.name
                for column in referenced_schema.expressions
            ]

            for column, reference_column in zip(
                constraint.expressions,
                referenced_columns,
            ):
                foreign_keys.append(
                    ForeignKey(
                        column=column.name,
                        referenced_table=referenced_table,
                        referenced_column=reference_column,
                    )
                )