import sqlglot
from sqlglot import expressions as exp

from .models import SQLStructure, ColumnReference


class SQLParser:
    def __init__(self, dialect: str | None = None):
        self.dialect = dialect

    def parse(self, sql: str) -> SQLStructure:

        expression = sqlglot.parse_one(sql, read=self.dialect)

        result = SQLStructure()

        self._extract_tables(expression, result)
        self._extract_columns(expression, result)

        return result

    def _extract_tables(self, expression, result):

        for table in expression.find_all(exp.Table):

            name = table.name

            if name not in result.tables:
                result.tables.append(name)

    def _extract_columns(self, expression, result):

        for column in expression.find_all(exp.Column):

            result.select_columns.append(
                ColumnReference(
                    table=column.table or None,
                    column=column.name,
                )
            )
