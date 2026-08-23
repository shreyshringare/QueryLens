import sqlglot
from sqlglot import expressions as exp

from .models import SQLStructure, ColumnReference, Join, Filter


class SQLParser:
    def __init__(self, dialect: str | None = None):
        self.dialect = dialect

    def parse(self, sql: str) -> SQLStructure:

        expression = sqlglot.parse_one(sql, read=self.dialect)

        result = SQLStructure()

        self._extract_tables(expression, result)
        self._extract_columns(expression, result)
        self._extract_joins(expression, result)
        self._extract_filters(expression, result)

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

    def _extract_joins(self, expression, result):
        # Known limitations: only the first column pair in a multi-column ON
        # condition is captured (e.g. "ON a.x = b.x AND a.y = b.y" loses the
        # second pair), and JOIN ... USING (...) produces no ON condition so
        # such joins are silently skipped entirely.

        for join in expression.find_all(exp.Join):

            table = join.this

            if not isinstance(table, exp.Table):
                continue

            condition = join.args.get("on")

            if condition is None:
                continue

            columns = list(condition.find_all(exp.Column))

            if len(columns) < 2:
                continue

            left, right = columns[0], columns[1]

            result.joins.append(
                Join(
                    join_type=" ".join(
                        part for part in (join.args.get("side"), join.args.get("kind")) if part
                    ) or "JOIN",
                    table=table.name,
                    left=ColumnReference(table=left.table or None, column=left.name),
                    right=ColumnReference(table=right.table or None, column=right.name),
                )
            )

    def _extract_filters(self, expression, result):

        where = expression.args.get("where")

        if where is None:
            return

        # exp.Predicate matches only real comparison ops (EQ, GT, Like, In, ...).
        # A plain exp.Condition would also match bare Column/Literal nodes,
        # since those are Condition subclasses too in sqlglot 27.x.
        for predicate in where.find_all(exp.Predicate):

            columns = list(predicate.find_all(exp.Column))

            if not columns:
                continue

            column = columns[0]

            result.filters.append(
                Filter(
                    column=ColumnReference(table=column.table or None, column=column.name),
                    operator=predicate.key.upper(),
                    value=predicate.sql(),
                )
            )
