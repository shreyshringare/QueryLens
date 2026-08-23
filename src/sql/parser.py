import sqlglot
from sqlglot import expressions as exp

from .models import SQLStructure, ColumnReference, Join, Filter, Aggregation, OrderBy


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
        self._extract_aggregations(expression, result)
        self._extract_group_by(expression, result)
        self._extract_order_by(expression, result)

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
        #
        # Known limitation: only the first column found in a predicate is
        # recorded in the structured `column` field, so column-to-column
        # comparisons (e.g. "o.a = o.b") or predicates where both sides
        # reference columns (e.g. "BETWEEN o.min_amt AND o.max_amt") only
        # capture one side there — the full text is still preserved in `value`.
        for predicate in where.find_all(exp.Predicate):

            columns = list(predicate.find_all(exp.Column))

            if not columns:
                continue

            column = columns[0]

            negated = isinstance(predicate.parent, exp.Not)
            operator = predicate.key.upper()
            value = predicate.sql()

            if negated:
                operator = f"NOT {operator}"
                value = predicate.parent.sql()

            result.filters.append(
                Filter(
                    column=ColumnReference(table=column.table or None, column=column.name),
                    operator=operator,
                    value=value,
                )
            )

    def _extract_aggregations(self, expression, result):
        # Known limitations: only the first Column found inside the aggregate's
        # argument is captured (e.g. "SUM(o.amount + o.tax)" only records
        # o.amount, silently dropping o.tax — same columns[0] tradeoff as
        # _extract_joins/_extract_filters). Window-function aggregates
        # (e.g. "SUM(x) OVER (PARTITION BY ...)") are also swept in here
        # indistinguishably from reducing aggregates — the PARTITION BY/ORDER
        # BY columns themselves are NOT captured (they're siblings of the
        # AggFunc node, not descendants), but the aggregate itself is still
        # recorded as if it were a regular GROUP BY-style aggregate.

        for node in expression.find_all(exp.AggFunc):

            columns = list(node.find_all(exp.Column))

            column = None
            if columns:
                first = columns[0]
                column = ColumnReference(table=first.table or None, column=first.name)

            result.aggregations.append(
                Aggregation(function=node.sql_name().upper(), column=column)
            )

    def _extract_group_by(self, expression, result):
        # Known limitation: GROUP BY ROLLUP(...)/CUBE(...)/GROUPING SETS (...)
        # store their columns under separate Group args ("rollup", "cube",
        # "grouping_sets") rather than in group.expressions, so those variants
        # are silently skipped here — group_by comes back empty for them.
        # Ordinal GROUP BY (e.g. "GROUP BY 1") is also a no-op by design: the
        # item is a bare Literal with no Column descendants to find.

        group = expression.args.get("group")

        if group is None:
            return

        for item in group.expressions:

            for column in item.find_all(exp.Column):

                result.group_by.append(
                    ColumnReference(table=column.table or None, column=column.name)
                )

    def _extract_order_by(self, expression, result):
        # Known limitation: NULLS FIRST/NULLS LAST is parsed by sqlglot into a
        # separate `nulls_first` arg on each Ordered node, independent of
        # `desc`, so the direction extraction below is unaffected by it — but
        # that information itself is silently discarded since OrderBy has no
        # field for it.

        order = expression.args.get("order")

        if order is None:
            return

        for item in order.expressions:

            direction = "DESC" if item.args.get("desc") else "ASC"

            result.order_by.append(
                OrderBy(expression=item.this.sql(), direction=direction)
            )
