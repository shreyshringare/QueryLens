# Phase 2 — SQL Structure & Schema↔SQL Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Parse ground-truth SQL into a structured `SQLStructure` representation, resolve table aliases against the already-built `DatabaseSchema`, validate SQL references against schema, and produce `data/structured/structured.jsonl` combining Phase-1 normalized records with parsed schema + SQL structure.

**Post-plan follow-ups (found during the final whole-branch review after all 16 tasks completed):**
- **Task 17 — CTE names treated as real tables:** `_extract_tables` matched every `exp.Table` node including CTE (`WITH x AS (...)`) references, causing `SQLSchemaValidator` to falsely flag `"Unknown table: x"` for any query using a CTE. Fixed by excluding CTE names via `expression.find_all(exp.CTE)`. A second-round review then found the naive fix had its own bug: a CTE that self-references a real table of the same name (`WITH orders AS (SELECT ... FROM orders ...) SELECT * FROM orders` — standard non-recursive SQL, the inner `orders` means the real table) caused the real table to be silently dropped from `result.tables` entirely (worse than the original bug — a silent false-negative instead of a loud false-positive). Fixed using `table.find_ancestor(exp.CTE)` to distinguish a genuine CTE reference from a same-named real-table self-reference inside the CTE's own body. A residual, documented-not-fixed gap remains: a *qualified* CTE column reference (`SELECT recent.customer_id FROM recent`) still produces a false positive, converted from an "Unknown table" error to an "Unknown column" error, since `_resolve_aliases` doesn't share `_extract_tables`'s `cte_names` set — fixing that would require passing CTE awareness into alias resolution too, out of scope for this fix.
- **Task 18 — SQLSchemaValidator never wired into the pipeline:** the plan's stated Goal includes validating SQL against schema, but `transform_record()` in `scripts/build_structured_dataset.py` never called `SQLSchemaValidator` — it was built and tested in isolation (Task 13) but dead code from the shipped pipeline's perspective. Fixed by calling it and adding a `validation_errors` key to the output. Re-ran against all 6 real records — all show `validation_errors: []` (the dataset's ground-truth SQL is clean relative to its own DDL). Added a scope-limiting comment at the call site (only checks `.tables`/qualified `.select_columns`, not joins/filters/aggregations/group_by, silently skips unqualified columns) so downstream consumers of `structured.jsonl` don't over-trust an empty list.

**Final state:** 18/18 tasks complete (16 planned + 2 follow-ups from final whole-branch review). Full suite: 143 passed, 0 failed.

**Architecture:** `SQLParser` (sqlglot-based) extracts tables/columns/joins/filters/aggregations/group-by/order-by/limit into `SQLStructure`. An `AliasResolver` built from the same parse tree rewrites `c.name` → `customers.name` so results line up with `DatabaseSchema`. `SQLSchemaValidator` (added to the existing `src/schema/validator.py`) then flags unknown tables/columns. A pipeline script ties `SchemaParser` + `SQLParser` together over `data/processed/normalized.jsonl`.

**Tech Stack:** Python 3.14 (project venv at `.venv`), sqlglot 27.14.0, pytest, dataclasses.

**Already done (do not redo):** `src/schema/models.py`, `src/schema/parser.py` (DDL parsing incl. foreign keys), `src/schema/relationships.py` + `src/schema/relationship_graph.py`, `src/schema/serializer.py`, base `src/schema/validator.py::SchemaValidator` (duplicate table/column check), and their tests (`test_schema_parser.py`, `test_schema_relationships.py`, `test_schema_validator.py::test_schema_to_dict`, `::test_schema_to_json`) all exist and pass.

**Important environment note:** This repo has a project venv at `.venv`. The system `python`/`pip` do NOT have `sqlglot`/`pytest` installed. Every command below MUST use the venv interpreter directly:
- Windows Git Bash: `.venv/Scripts/python.exe -m pytest ...`
- PowerShell: `.venv\Scripts\python.exe -m pytest ...`

**Correction vs. the original spec:**
- Phase 1 output actually lives at `data/processed/normalized.jsonl` (not `data/normalized/normalized.jsonl`). The pipeline script in this plan uses the real path.
- `sql_structure.__dict__` does NOT recursively convert nested dataclasses (`ColumnReference`, `Join`, `Filter`, `Aggregation`, `OrderBy`) to plain dicts — `json.dumps` would throw `TypeError: Object of type ColumnReference is not JSON serializable`. This plan uses `dataclasses.asdict(sql_structure)` instead, same as the existing schema serializer.
- The spec's WHERE-clause extractor used `expression.find_all(sqlglot.expressions.Condition)`, which also matches bare `Column` and `Literal` nodes (they're `Condition` subclasses in sqlglot 27.x) and produces garbage filter entries. This plan uses `sqlglot.expressions.Predicate` instead, which matches only actual comparison ops (`EQ`, `GT`, `Like`, `In`, …) — verified against the installed sqlglot version.
- The spec's aggregation extractor manually walks `expression.walk()`; `expression.find_all(sqlglot.expressions.AggFunc)` does the same thing more simply and was verified to work identically.

---

## File Structure

- `src/sql/models.py` — `ColumnReference`, `Join`, `Filter`, `Aggregation`, `OrderBy`, `SQLStructure` dataclasses (currently empty stub).
- `src/sql/parser.py` — `SQLParser` class, one `_extract_*` method per SQL clause (currently empty stub).
- `src/sql/aliases.py` — `AliasResolver` (new file, not in the original stub list but required by Step 25 of the spec).
- `src/sql/__init__.py` — re-exports (currently empty stub).
- `src/schema/validator.py` — **modify**: add `SQLSchemaValidator` alongside the existing `SchemaValidator`.
- `scripts/build_structured_dataset.py` — pipeline script (currently empty stub).
- `tests/test_sql_parser.py` — one test per extractor (currently empty stub).
- `tests/test_schema_validator.py` — **modify**: add `SQLSchemaValidator` tests.
- `tests/test_build_structured_dataset.py` — new, tests the script's pure transform function.
- `tests/test_phase2_integration.py` — full DDL+SQL → schema+structure → validate pipeline (currently empty stub).

---

### Task 1: SQL structure models

**Files:**
- Modify: `src/sql/models.py` (currently empty)
- Test: `tests/test_sql_parser.py` (currently empty)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sql_parser.py
from src.sql.models import (
    ColumnReference,
    Join,
    Filter,
    Aggregation,
    OrderBy,
    SQLStructure,
)


def test_sql_structure_defaults():

    structure = SQLStructure()

    assert structure.select_columns == []
    assert structure.tables == []
    assert structure.joins == []
    assert structure.filters == []
    assert structure.aggregations == []
    assert structure.group_by == []
    assert structure.order_by == []
    assert structure.limit is None


def test_sql_structure_holds_values():

    ref = ColumnReference(table="customers", column="name")

    structure = SQLStructure(
        select_columns=[ref],
        tables=["customers"],
        limit=10,
    )

    assert structure.select_columns == [ref]
    assert structure.tables == ["customers"]
    assert structure.limit == 10
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_sql_parser.py -v`
Expected: FAIL / ERROR — `ImportError: cannot import name 'ColumnReference' from 'src.sql.models'` (module is empty)

- [ ] **Step 3: Write minimal implementation**

```python
# src/sql/models.py
from dataclasses import dataclass, field


@dataclass
class ColumnReference:
    table: str | None
    column: str


@dataclass
class Join:
    join_type: str
    table: str
    left: ColumnReference
    right: ColumnReference


@dataclass
class Filter:
    column: ColumnReference
    operator: str
    value: str


@dataclass
class Aggregation:
    function: str
    column: ColumnReference | None


@dataclass
class OrderBy:
    expression: str
    direction: str


@dataclass
class SQLStructure:
    select_columns: list[ColumnReference] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)
    joins: list[Join] = field(default_factory=list)
    filters: list[Filter] = field(default_factory=list)
    aggregations: list[Aggregation] = field(default_factory=list)
    group_by: list[ColumnReference] = field(default_factory=list)
    order_by: list[OrderBy] = field(default_factory=list)
    limit: int | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_sql_parser.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/sql/models.py tests/test_sql_parser.py
git commit -m "feat(sql): add SQLStructure dataclasses"
```

---

### Task 2: SQL package exports

**Files:**
- Modify: `src/sql/__init__.py` (currently empty)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sql_parser.py  (append)
def test_sql_package_exports():
    from src.sql import ColumnReference, SQLStructure  # noqa: F401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_sql_parser.py::test_sql_package_exports -v`
Expected: FAIL — `ImportError: cannot import name 'ColumnReference' from 'src.sql'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/sql/__init__.py
from .models import (
    ColumnReference,
    Join,
    Filter,
    Aggregation,
    OrderBy,
    SQLStructure,
)

__all__ = [
    "ColumnReference",
    "Join",
    "Filter",
    "Aggregation",
    "OrderBy",
    "SQLStructure",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_sql_parser.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/sql/__init__.py
git commit -m "feat(sql): export SQL structure models from package init"
```

---

### Task 3: SQLParser — table extraction

**Files:**
- Modify: `src/sql/parser.py` (currently empty)
- Test: `tests/test_sql_parser.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sql_parser.py  (append)
from src.sql.parser import SQLParser


def test_extract_tables():

    sql = """
    SELECT *
    FROM customers c
    JOIN orders o
        ON c.customer_id = o.customer_id
    """

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert result.tables == ["customers", "orders"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_sql_parser.py::test_extract_tables -v`
Expected: FAIL — `ImportError: cannot import name 'SQLParser' from 'src.sql.parser'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/sql/parser.py
import sqlglot
from sqlglot import expressions as exp

from .models import SQLStructure


class SQLParser:
    def __init__(self, dialect: str | None = None):
        self.dialect = dialect

    def parse(self, sql: str) -> SQLStructure:

        expression = sqlglot.parse_one(sql, read=self.dialect)

        result = SQLStructure()

        self._extract_tables(expression, result)

        return result

    def _extract_tables(self, expression, result):

        for table in expression.find_all(exp.Table):

            name = table.name

            if name not in result.tables:
                result.tables.append(name)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_sql_parser.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/sql/parser.py
git commit -m "feat(sql): extract table names in SQLParser"
```

---

### Task 4: SQLParser — column extraction

**Files:**
- Modify: `src/sql/parser.py`
- Test: `tests/test_sql_parser.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sql_parser.py  (append)
from src.sql.models import ColumnReference


def test_extract_columns():

    sql = """
    SELECT c.name, o.order_id
    FROM customers c
    JOIN orders o
        ON c.customer_id = o.customer_id
    """

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert ColumnReference(table="c", column="name") in result.select_columns
    assert ColumnReference(table="o", column="order_id") in result.select_columns
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_sql_parser.py::test_extract_columns -v`
Expected: FAIL — `AssertionError` (`select_columns` still empty; `_extract_columns` not called)

- [ ] **Step 3: Write minimal implementation**

```python
# src/sql/parser.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_sql_parser.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/sql/parser.py
git commit -m "feat(sql): extract column references in SQLParser"
```

---

### Task 5: SQLParser — join extraction

**Files:**
- Modify: `src/sql/parser.py`
- Test: `tests/test_sql_parser.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sql_parser.py  (append)
from src.sql.models import Join


def test_extract_joins():

    sql = """
    SELECT *
    FROM customers c
    JOIN orders o
        ON c.customer_id = o.customer_id
    """

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert len(result.joins) == 1

    join = result.joins[0]

    assert join.table == "orders"
    assert join.left == ColumnReference(table="c", column="customer_id")
    assert join.right == ColumnReference(table="o", column="customer_id")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_sql_parser.py::test_extract_joins -v`
Expected: FAIL — `AssertionError: 0 == 1` (`joins` still empty)

- [ ] **Step 3: Write minimal implementation**

```python
# src/sql/parser.py
import sqlglot
from sqlglot import expressions as exp

from .models import SQLStructure, ColumnReference, Join


class SQLParser:
    def __init__(self, dialect: str | None = None):
        self.dialect = dialect

    def parse(self, sql: str) -> SQLStructure:

        expression = sqlglot.parse_one(sql, read=self.dialect)

        result = SQLStructure()

        self._extract_tables(expression, result)
        self._extract_columns(expression, result)
        self._extract_joins(expression, result)

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
```

**Post-hoc correction (found during Task 5's code quality review, verified against sqlglot 27.14.0):** the original `join_type=join.args.get("kind") or "JOIN"` only reads sqlglot's `kind` arg (INNER/OUTER/CROSS), dropping the separate `side` arg (LEFT/RIGHT/FULL) entirely — `LEFT JOIN` was mislabeled `"JOIN"`, and `RIGHT OUTER JOIN`/`FULL OUTER JOIN` both collapsed to the indistinguishable `"OUTER"`. The snippet above combines both args. `_extract_joins` also has two known, intentionally-undocumented-until-now limitations: a multi-column `ON` condition (e.g. `ON a.x = b.x AND a.y = b.y`) only captures the first column pair, and `JOIN ... USING (...)` produces no `on` arg so such joins are silently skipped entirely — both are out of scope to fix (the `Join` model only supports one left/right pair) but should carry a comment in the code so nobody assumes completeness later.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_sql_parser.py -v`
Expected: PASS (8 tests — includes a `LEFT JOIN` case asserting `join_type`, added during Task 5's review loop)

- [ ] **Step 5: Commit**

```bash
git add src/sql/parser.py
git commit -m "feat(sql): extract joins in SQLParser"
```

---

### Task 6: SQLParser — WHERE / filter extraction

**Files:**
- Modify: `src/sql/parser.py`
- Test: `tests/test_sql_parser.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sql_parser.py  (append)
def test_extract_filters():

    sql = """
    SELECT *
    FROM orders o
    WHERE o.amount > 1000
      AND o.status = 'shipped'
    """

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert len(result.filters) == 2

    operators = {f.operator for f in result.filters}
    assert operators == {"GT", "EQ"}

    amount_filter = next(f for f in result.filters if f.operator == "GT")
    assert amount_filter.column == ColumnReference(table="o", column="amount")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_sql_parser.py::test_extract_filters -v`
Expected: FAIL — `AssertionError: 0 == 2` (`filters` still empty)

- [ ] **Step 3: Write minimal implementation**

```python
# src/sql/parser.py
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
                    join_type=join.args.get("kind") or "JOIN",
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
        # A plain exp.Condition would also match bare Column/Literal nodes.
        # Known limitation: only the first Column found in a predicate is
        # captured in the structured `column` field, so column-to-column
        # comparisons (e.g. "WHERE o.a = o.b") or dual-column bounds (e.g.
        # "BETWEEN o.min_amt AND o.max_amt") only record one side there —
        # the full text is still preserved in `value`.
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
```

**Post-hoc correction (found during Task 6's code quality review, verified against sqlglot 27.14.0):** the original snippet read `predicate.key`/`predicate.sql()` off the matched `Predicate` node only, never checking whether it was wrapped in `exp.Not` — so `c.email IS NOT NULL` was extracted as `operator="IS", value="c.email IS NULL"`, the exact opposite of what was written (same for `NOT LIKE`/`NOT IN`, negation silently dropped). The snippet above checks `predicate.parent` for `exp.Not` and prefixes the operator / uses the wrapper's `.sql()` when negated.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_sql_parser.py -v`
Expected: PASS (13 tests — includes 3 extra coverage tests added during Task 6's review: LIKE predicate, no-WHERE-clause, bare-column-no-spurious-filter, plus a negation regression test from the fix above)

- [ ] **Step 5: Commit**

```bash
git add src/sql/parser.py
git commit -m "feat(sql): extract WHERE filters using exp.Predicate"
```

---

### Task 7: SQLParser — aggregation extraction

**Files:**
- Modify: `src/sql/parser.py`
- Test: `tests/test_sql_parser.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sql_parser.py  (append)
def test_extract_aggregations():

    sql = "SELECT COUNT(o.order_id), SUM(o.amount) FROM orders o"

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert len(result.aggregations) == 2

    functions = {a.function for a in result.aggregations}
    assert functions == {"COUNT", "SUM"}

    count_agg = next(a for a in result.aggregations if a.function == "COUNT")
    assert count_agg.column == ColumnReference(table="o", column="order_id")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_sql_parser.py::test_extract_aggregations -v`
Expected: FAIL — `AssertionError: 0 == 2` (`aggregations` still empty)

- [ ] **Step 3: Write minimal implementation**

Add `Aggregation` to the model import and add `_extract_aggregations`, calling it from `parse()`:

```python
# src/sql/parser.py  (relevant additions only — full file below)
from .models import SQLStructure, ColumnReference, Join, Filter, Aggregation
```

```python
    def parse(self, sql: str) -> SQLStructure:

        expression = sqlglot.parse_one(sql, read=self.dialect)

        result = SQLStructure()

        self._extract_tables(expression, result)
        self._extract_columns(expression, result)
        self._extract_joins(expression, result)
        self._extract_filters(expression, result)
        self._extract_aggregations(expression, result)

        return result
```

```python
    def _extract_aggregations(self, expression, result):
        # Known limitations: only the first Column found inside the aggregate's
        # argument is captured (e.g. "SUM(o.amount + o.tax)" only records
        # o.amount, silently dropping o.tax — same columns[0] tradeoff as
        # _extract_joins/_extract_filters). Window-function aggregates
        # (e.g. "SUM(x) OVER (PARTITION BY ...)") are also swept in here
        # indistinguishably from reducing aggregates — the PARTITION BY/ORDER
        # BY columns themselves are NOT captured (siblings of the AggFunc
        # node, not descendants), but the aggregate itself is still recorded
        # as if it were a regular GROUP BY-style aggregate.

        for node in expression.find_all(exp.AggFunc):

            columns = list(node.find_all(exp.Column))

            column = None
            if columns:
                first = columns[0]
                column = ColumnReference(table=first.table or None, column=first.name)

            result.aggregations.append(
                Aggregation(function=node.sql_name().upper(), column=column)
            )
```

**Post-hoc note (Task 7's code quality review):** the comment above was added after review flagged that the multi-column-argument limitation (mirroring `_extract_joins`/`_extract_filters`) wasn't documented, and that window-aggregate inclusion needed a regression test. No production logic changed — see `tests/test_sql_parser.py::test_extract_aggregations_count_star` and `::test_extract_aggregations_window_function_included`.

Full `src/sql/parser.py` after this step (illustrative — predates the Task 5/6 post-hoc fixes noted above; the real file has those fixes applied):

```python
# src/sql/parser.py
import sqlglot
from sqlglot import expressions as exp

from .models import SQLStructure, ColumnReference, Join, Filter, Aggregation


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
                    join_type=join.args.get("kind") or "JOIN",
                    table=table.name,
                    left=ColumnReference(table=left.table or None, column=left.name),
                    right=ColumnReference(table=right.table or None, column=right.name),
                )
            )

    def _extract_filters(self, expression, result):

        where = expression.args.get("where")

        if where is None:
            return

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

    def _extract_aggregations(self, expression, result):

        for node in expression.find_all(exp.AggFunc):

            columns = list(node.find_all(exp.Column))

            column = None
            if columns:
                first = columns[0]
                column = ColumnReference(table=first.table or None, column=first.name)

            result.aggregations.append(
                Aggregation(function=node.sql_name().upper(), column=column)
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_sql_parser.py -v`
Expected: PASS (16 tests — includes `test_extract_aggregations_count_star` and `test_extract_aggregations_window_function_included`, added during Task 7's review to lock in documented-but-untested edge cases)

- [ ] **Step 5: Commit**

```bash
git add src/sql/parser.py
git commit -m "feat(sql): extract aggregations in SQLParser"
```

---

### Task 8: SQLParser — GROUP BY extraction

**Post-hoc note (Task 8's code quality review):** implementer proactively documented (not fixed) a real gap — `GROUP BY ROLLUP(...)/CUBE(...)/GROUPING SETS (...)` produce an empty `group.expressions`, so those columns are silently dropped from `result.group_by`. Verified correct by review. Two follow-up tests were added: `test_extract_group_by_absent` (no GROUP BY clause) and `test_extract_group_by_multiple_columns`.

**Files:**
- Modify: `src/sql/parser.py`
- Test: `tests/test_sql_parser.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sql_parser.py  (append)
def test_extract_group_by():

    sql = "SELECT c.name, COUNT(*) FROM customers c GROUP BY c.name"

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert result.group_by == [ColumnReference(table="c", column="name")]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_sql_parser.py::test_extract_group_by -v`
Expected: FAIL — `AssertionError: [] == [ColumnReference(...)]`

- [ ] **Step 3: Write minimal implementation**

Add the call in `parse()` and the method:

```python
        self._extract_aggregations(expression, result)
        self._extract_group_by(expression, result)

        return result
```

```python
    def _extract_group_by(self, expression, result):

        group = expression.args.get("group")

        if group is None:
            return

        for item in group.expressions:

            for column in item.find_all(exp.Column):

                result.group_by.append(
                    ColumnReference(table=column.table or None, column=column.name)
                )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_sql_parser.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add src/sql/parser.py
git commit -m "feat(sql): extract GROUP BY columns in SQLParser"
```

---

### Task 9: SQLParser — ORDER BY extraction

**Files:**
- Modify: `src/sql/parser.py`
- Test: `tests/test_sql_parser.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sql_parser.py  (append)
from src.sql.models import OrderBy


def test_extract_order_by():

    sql = "SELECT * FROM orders o ORDER BY o.amount DESC"

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert len(result.order_by) == 1
    assert result.order_by[0].direction == "DESC"
    assert "amount" in result.order_by[0].expression
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_sql_parser.py::test_extract_order_by -v`
Expected: FAIL — `AssertionError: 0 == 1`

- [ ] **Step 3: Write minimal implementation**

```python
        self._extract_group_by(expression, result)
        self._extract_order_by(expression, result)

        return result
```

```python
    def _extract_order_by(self, expression, result):

        order = expression.args.get("order")

        if order is None:
            return

        for item in order.expressions:

            direction = "DESC" if item.args.get("desc") else "ASC"

            result.order_by.append(
                OrderBy(expression=item.this.sql(), direction=direction)
            )
```

Add `OrderBy` to the models import line at the top of `src/sql/parser.py`:

```python
from .models import SQLStructure, ColumnReference, Join, Filter, Aggregation, OrderBy
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_sql_parser.py -v`
Expected: PASS (10 tests)

- [ ] **Step 5: Commit**

```bash
git add src/sql/parser.py
git commit -m "feat(sql): extract ORDER BY in SQLParser"
```

---

### Task 10: SQLParser — LIMIT extraction

**Post-hoc note (Task 10's code quality review, last of the 8 extractor tasks):** the `except (TypeError, ValueError, AttributeError)` branch is real and reachable — Oracle's `FETCH FIRST N ROWS ONLY` parses to `exp.Fetch`, whose `.expression` property returns `None` (count is stored under a different key), so `.expression.this` raises `AttributeError`. Not an issue for this project's target dialects (postgres/mysql/sqlite/duckdb, all of which parse `LIMIT n` as `exp.Limit`). A regression test (`test_extract_limit_fetch_first_syntax_not_captured`) and a precision fix to the explanatory comment were added during review.

**Files:**
- Modify: `src/sql/parser.py`
- Test: `tests/test_sql_parser.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sql_parser.py  (append)
def test_extract_limit():

    sql = "SELECT * FROM orders o LIMIT 10"

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert result.limit == 10


def test_extract_limit_absent():

    sql = "SELECT * FROM orders o"

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert result.limit is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_sql_parser.py::test_extract_limit -v`
Expected: FAIL — `AssertionError: None == 10`

- [ ] **Step 3: Write minimal implementation**

```python
        self._extract_order_by(expression, result)
        self._extract_limit(expression, result)

        return result
```

```python
    def _extract_limit(self, expression, result):

        limit = expression.args.get("limit")

        if limit is None:
            return

        try:
            result.limit = int(limit.expression.this)
        except (TypeError, ValueError, AttributeError):
            result.limit = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_sql_parser.py -v`
Expected: PASS (12 tests)

- [ ] **Step 5: Commit**

```bash
git add src/sql/parser.py
git commit -m "feat(sql): extract LIMIT in SQLParser"
```

---

### Task 11: AliasResolver

**Files:**
- Create: `src/sql/aliases.py`
- Test: `tests/test_sql_parser.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sql_parser.py  (append)
from src.sql.aliases import AliasResolver


def test_alias_resolver():

    resolver = AliasResolver()
    resolver.add("c", "customers")
    resolver.add("o", "orders")

    assert resolver.resolve("c") == "customers"
    assert resolver.resolve("o") == "orders"
    assert resolver.resolve("customers") == "customers"  # unknown key -> passthrough
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_sql_parser.py::test_alias_resolver -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.sql.aliases'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/sql/aliases.py
class AliasResolver:

    def __init__(self):
        self.aliases: dict[str, str] = {}

    def add(self, alias: str, table: str):
        self.aliases[alias.lower()] = table

    def resolve(self, name: str) -> str:
        return self.aliases.get(name.lower(), name)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_sql_parser.py -v`
Expected: PASS (13 tests)

- [ ] **Step 5: Commit**

```bash
git add src/sql/aliases.py
git commit -m "feat(sql): add AliasResolver"
```

---

### Task 12: Wire alias resolution into SQLParser.parse()

**Post-hoc note (Task 12's code quality review, the highest-risk task so far):** the plan's own test-update prediction (3 tests) undercounted the actual blast radius — `_resolve_aliases` touches `select_columns`, `group_by`, `filters`, and `aggregations`, so 8 tests needed `table=` updates, not 3. All hardened assertions from earlier tasks (dedup counts, `join_type`, etc.) were preserved. Review also found a real, silent bug: `_resolve_aliases` builds one flat alias→table map across the WHOLE tree including subqueries, so a reused alias letter (e.g. `a`) in a subquery overwrites the outer scope's mapping, silently resolving outer columns to the wrong table. This mirrors the flat, scope-unaware traversal already used by every other extractor in the file (all 8 flatten across subquery boundaries) — a real fix requires scope-aware traversal throughout the class, out of scope for this task. Documented with a comment (matching the other 5 known-limitation comments) and a regression test that locks in current behavior rather than attempting a fix.

**Why:** `_extract_columns`/`_extract_joins`/`_extract_group_by` currently put the raw alias (`"c"`) in `ColumnReference.table`, not the real table name (`"customers"`). `SQLSchemaValidator` (Task 13) needs real table names to check against `DatabaseSchema`.

**Files:**
- Modify: `src/sql/parser.py`
- Test: `tests/test_sql_parser.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sql_parser.py  (append)
def test_alias_resolution_in_parse():

    sql = """
    SELECT c.name, o.order_id
    FROM customers c
    JOIN orders o
        ON c.customer_id = o.customer_id
    GROUP BY c.name
    """

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert ColumnReference(table="customers", column="name") in result.select_columns
    assert ColumnReference(table="orders", column="order_id") in result.select_columns

    join = result.joins[0]
    assert join.left == ColumnReference(table="customers", column="customer_id")
    assert join.right == ColumnReference(table="orders", column="customer_id")

    assert result.group_by == [ColumnReference(table="customers", column="name")]


def test_alias_resolution_no_alias_used():

    sql = "SELECT customers.name FROM customers"

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert ColumnReference(table="customers", column="name") in result.select_columns
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_sql_parser.py::test_alias_resolution_in_parse -v`
Expected: FAIL — `select_columns` still has `table="c"`, not `table="customers"`

- [ ] **Step 3: Write minimal implementation**

Add the resolution pass as the last step of `parse()`:

```python
from .aliases import AliasResolver
```

```python
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
        self._extract_limit(expression, result)
        self._resolve_aliases(expression, result)

        return result
```

```python
    def _resolve_aliases(self, expression, result):

        resolver = AliasResolver()

        for table in expression.find_all(exp.Table):
            resolver.add(table.alias_or_name, table.name)

        for ref in result.select_columns:
            if ref.table is not None:
                ref.table = resolver.resolve(ref.table)

        for ref in result.group_by:
            if ref.table is not None:
                ref.table = resolver.resolve(ref.table)

        for f in result.filters:
            if f.column.table is not None:
                f.column.table = resolver.resolve(f.column.table)

        for agg in result.aggregations:
            if agg.column is not None and agg.column.table is not None:
                agg.column.table = resolver.resolve(agg.column.table)

        for join in result.joins:
            if join.left.table is not None:
                join.left.table = resolver.resolve(join.left.table)
            if join.right.table is not None:
                join.right.table = resolver.resolve(join.right.table)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_sql_parser.py -v`
Expected: PASS (15 tests) — also re-check Tasks 4/5/8's earlier assertions (`table="c"`) now read `table="customers"`; those older tests (`test_extract_columns`, `test_extract_joins`, `test_extract_group_by`) will FAIL after this change since they asserted the raw alias.

- [ ] **Step 5: Update the now-outdated earlier assertions**

```python
# tests/test_sql_parser.py — update in place
def test_extract_columns():

    sql = """
    SELECT c.name, o.order_id
    FROM customers c
    JOIN orders o
        ON c.customer_id = o.customer_id
    """

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert ColumnReference(table="customers", column="name") in result.select_columns
    assert ColumnReference(table="orders", column="order_id") in result.select_columns
```

```python
def test_extract_joins():

    sql = """
    SELECT *
    FROM customers c
    JOIN orders o
        ON c.customer_id = o.customer_id
    """

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert len(result.joins) == 1

    join = result.joins[0]

    assert join.table == "orders"
    assert join.left == ColumnReference(table="customers", column="customer_id")
    assert join.right == ColumnReference(table="orders", column="customer_id")
```

```python
def test_extract_group_by():

    sql = "SELECT c.name, COUNT(*) FROM customers c GROUP BY c.name"

    parser = SQLParser(dialect="sqlite")

    result = parser.parse(sql)

    assert result.group_by == [ColumnReference(table="customers", column="name")]
```

- [ ] **Step 6: Run full file to verify all pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_sql_parser.py -v`
Expected: PASS (15 tests)

- [ ] **Step 7: Commit**

```bash
git add src/sql/parser.py tests/test_sql_parser.py
git commit -m "feat(sql): resolve table aliases to real table names in SQLParser"
```

---

### Task 13: SQLSchemaValidator

**Post-hoc note (Task 13's code quality review):** implementing this task's own spec test required fixing a real pre-existing bug in `src/schema/models.py::Table.get_column` — it raised `ValueError` on a missing column instead of returning `None`, so `DatabaseSchema.has_column` (which did `table.get_column(x) is not None`) could never actually return `False`, it just crashed. Fixed with a `try/except ValueError: return False` wrapper in `has_column`. Review then found a follow-on accuracy issue: `get_table`/`has_table` matched case-insensitively but `get_column`/`has_column` didn't, which could produce false-positive "Unknown column" errors on validly-cased queries — fixed by making `get_column`'s comparison case-insensitive too, matching `get_table`'s existing pattern. Both fixes are minimal, single-line changes with regression tests. Note for Task 15: `SQLSchemaValidator.validate()` only checks `.tables` and `.select_columns` — `.joins`/`.filters`/`.aggregations`/`.group_by` are unchecked and unqualified columns are silently skipped, both intentionally scoped out and documented in-code, not oversights.

**Files:**
- Modify: `src/schema/validator.py`
- Test: `tests/test_schema_validator.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_schema_validator.py  (append)
from src.schema.models import ForeignKey
from src.schema.validator import SQLSchemaValidator
from src.sql.models import SQLStructure, ColumnReference


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
```

Update the existing import line at the top of `tests/test_schema_validator.py` (it currently imports `Column, Table, DatabaseSchema` — `ForeignKey` is imported above but unused; drop it to avoid an unused import, since none of these tests construct foreign keys):

```python
from src.schema.models import (
    Column,
    Table,
    DatabaseSchema,
)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_validator.py -v`
Expected: FAIL — `ImportError: cannot import name 'SQLSchemaValidator' from 'src.schema.validator'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/schema/validator.py
from .models import DatabaseSchema
from src.sql.models import SQLStructure


class SchemaValidator:

    def validate(self, schema: DatabaseSchema) -> list[str]:

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

    def validate(self, sql_structure: SQLStructure) -> list[str]:

        errors = []

        for table_name in sql_structure.tables:

            if not self.schema.has_table(table_name):
                errors.append(f"Unknown table: {table_name}")

        for reference in sql_structure.select_columns:

            if reference.table is None:
                continue

            if not self.schema.has_column(reference.table, reference.column):
                errors.append(
                    f"Unknown column: {reference.table}.{reference.column}"
                )

        return errors
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_validator.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/schema/validator.py tests/test_schema_validator.py
git commit -m "feat(schema): add SQLSchemaValidator for cross-checking SQL against DatabaseSchema"
```

---

### Task 14: Pipeline script — build_structured_dataset.py

**Post-hoc note (Task 14's code quality review):** ran successfully end-to-end against all 6 real records in `data/processed/normalized.jsonl` (dialect `duckdb`, multi-table schemas with foreign keys) — no crashes, validating the 8 extractors + alias resolution against real (if synthetic) data, not just hand-crafted unit fixtures. Review found `main()` had no per-record error handling (one bad record would crash the whole run, losing all output) — fixed to match the established try/except-per-record + counter + summary pattern already used by the sibling `scripts/build_normalized_dataset.py`. A separate reviewer observation that `select_columns`/`aggregations` contain WHERE-clause columns and duplicates was correctly identified as a false alarm — that's the intentional, already-tested broad-sweep/no-dedup design from Tasks 4 and 7, not a new bug. Also confirmed (pre-existing, out of scope): `python scripts/*.py` direct invocation fails without `PYTHONPATH=.` repo-wide — affects `build_normalized_dataset.py` too, not introduced here.

**Files:**
- Modify: `scripts/build_structured_dataset.py` (currently empty)
- Test: `tests/test_build_structured_dataset.py` (new)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_build_structured_dataset.py
from scripts.build_structured_dataset import transform_record


def test_transform_record():

    record = {
        "id": "0",
        "source": "synthetic",
        "domain": "general",
        "dialect": "sqlite",
        "database_id": "shop",
        "nl_question": "How many customers are there?",
        "ground_truth_sql": "SELECT COUNT(*) FROM customers",
        "ddl": "CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, name TEXT);",
        "metadata": {},
    }

    output = transform_record(record)

    assert output["id"] == "0"
    assert output["nl_question"] == "How many customers are there?"

    assert output["schema"]["database_id"] == "shop"
    assert output["schema"]["tables"][0]["name"] == "customers"

    assert output["sql_structure"]["tables"] == ["customers"]
    assert output["sql_structure"]["aggregations"][0]["function"] == "COUNT"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_build_structured_dataset.py -v`
Expected: FAIL — `ImportError: cannot import name 'transform_record' from 'scripts.build_structured_dataset'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/build_structured_dataset.py
import json
from dataclasses import asdict
from pathlib import Path

from src.schema.parser import SchemaParser
from src.schema.serializer import schema_to_dict
from src.sql.parser import SQLParser


INPUT = Path("data/processed/normalized.jsonl")
OUTPUT = Path("data/structured/structured.jsonl")


def transform_record(record: dict) -> dict:

    database_id = record["database_id"]
    dialect = record.get("dialect")
    ddl = record.get("ddl", "")
    sql = record["ground_truth_sql"]

    schema = SchemaParser(dialect=dialect).parse(
        database_id=database_id,
        ddl=ddl,
    )

    sql_structure = SQLParser(dialect=dialect).parse(sql)

    output = dict(record)
    output["schema"] = schema_to_dict(schema)
    output["sql_structure"] = asdict(sql_structure)

    return output


def main():

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with (
        INPUT.open("r", encoding="utf-8") as source,
        OUTPUT.open("w", encoding="utf-8") as target,
    ):

        for line in source:

            record = json.loads(line)
            output = transform_record(record)

            target.write(json.dumps(output, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_build_structured_dataset.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Run against the real Phase-1 output**

Run: `.venv/Scripts/python.exe scripts/build_structured_dataset.py`
Then: `.venv/Scripts/python.exe -c "import json; print(json.dumps(json.loads(open('data/structured/structured.jsonl', encoding='utf-8').readline()), indent=2)[:1000])"`
Expected: prints one structured record with populated `schema` and `sql_structure` keys, no traceback. If any real record's DDL/SQL fails to parse, note the record `id` and dialect — do not silently swallow the error; surface it so the failing DDL/SQL can be inspected (out of scope for this plan to fix parser gaps for pathological input).

- [ ] **Step 6: Commit**

```bash
git add scripts/build_structured_dataset.py tests/test_build_structured_dataset.py
git commit -m "feat(pipeline): build structured.jsonl from normalized records"
```

---

### Task 15: Phase-2 integration test

**Files:**
- Modify: `tests/test_phase2_integration.py` (currently empty)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_phase2_integration.py
from src.schema.parser import SchemaParser
from src.schema.validator import SQLSchemaValidator
from src.sql.parser import SQLParser


def test_phase2_pipeline_valid_query_has_no_errors():

    ddl = """
    CREATE TABLE customers (
        customer_id INTEGER PRIMARY KEY,
        name TEXT
    );

    CREATE TABLE orders (
        order_id INTEGER PRIMARY KEY,
        customer_id INTEGER,
        amount DECIMAL,
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    );
    """

    sql = """
    SELECT c.name, COUNT(o.order_id)
    FROM customers c
    JOIN orders o
        ON c.customer_id = o.customer_id
    GROUP BY c.name
    """

    schema = SchemaParser(dialect="sqlite").parse(database_id="shop", ddl=ddl)

    assert schema.has_table("customers")
    assert schema.has_table("orders")

    structure = SQLParser(dialect="sqlite").parse(sql)

    assert "customers" in structure.tables
    assert "orders" in structure.tables
    assert len(structure.aggregations) == 1
    assert len(structure.group_by) == 1

    errors = SQLSchemaValidator(schema).validate(structure)

    assert errors == []


def test_phase2_pipeline_flags_typo_column():

    ddl = """
    CREATE TABLE customers (
        customer_id INTEGER PRIMARY KEY,
        name TEXT
    );
    """

    sql = "SELECT customer_name FROM customers"

    schema = SchemaParser(dialect="sqlite").parse(database_id="shop", ddl=ddl)
    structure = SQLParser(dialect="sqlite").parse(sql)

    errors = SQLSchemaValidator(schema).validate(structure)

    assert errors == ["Unknown column: customers.customer_name"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_phase2_integration.py -v`
Expected: FAIL until Tasks 1-13 are complete (should already PASS at this point if run in order — run it anyway to confirm end-to-end wiring, since this test exercises no new production code).

- [ ] **Step 3: No new implementation needed**

This test only exercises `SchemaParser`, `SQLParser`, and `SQLSchemaValidator` built in earlier tasks — it verifies they compose correctly.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_phase2_integration.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/test_phase2_integration.py
git commit -m "test: add Phase 2 end-to-end schema+SQL integration test"
```

---

### Task 16: Full Phase-2 test suite run

**Result:** all 43 Phase-2 tests pass; full repo suite (`tests/`) is 138 passed, 0 failed — no regressions in Phase 1 (data_pipeline, adapters, validation, split) or anywhere else.

**Files:** none (verification only)

- [ ] **Step 1: Run every Phase-2-relevant test file**

Run:
```bash
.venv/Scripts/python.exe -m pytest tests/test_schema_parser.py tests/test_schema_relationships.py tests/test_schema_validator.py tests/test_sql_parser.py tests/test_build_structured_dataset.py tests/test_phase2_integration.py -v
```
Expected: all PASS, no errors or warnings about missing modules (confirms the `.venv` interpreter is being used).

- [ ] **Step 2: Confirm no regression in the rest of the suite**

Run: `.venv/Scripts/python.exe -m pytest tests/ -v 2>&1 | tail -40`
Expected: only pre-existing, unrelated failures if any (e.g. environment gaps for `pyspark`-dependent tests outside this plan's scope) — nothing newly broken in `src/schema/` or `src/sql/`.

---

## Self-Review Notes

- **Spec coverage:** Checkpoints A/B (schema DDL parsing, relationships, serialization, duplicate-name validation) were already implemented before this plan and are left untouched. Checkpoint C (SQL parsing: tables, columns, joins, filters, aggregations, group by, order by, limit) → Tasks 3-10. Checkpoint D (alias resolution, schema↔SQL validation, pipeline script, integration test) → Tasks 11-15. The spec's `Relationship`/`extract_relationships`/`schema_to_dict` steps (9-10) and `SchemaValidator` (step 11) are already done and were not re-planned.
- **Placeholder scan:** every step has real, complete code; no "TBD"/"add later" markers.
- **Type consistency:** `ColumnReference`, `Join`, `Filter`, `Aggregation`, `OrderBy`, `SQLStructure` are defined once in Task 1 and used with identical field names throughout Tasks 3-15. `SQLSchemaValidator(schema).validate(structure)` signature is defined in Task 13 and used unchanged in Tasks 14-15.
- **Deviations from the pasted spec, all called out inline above:** real `data/processed/normalized.jsonl` path (not `data/normalized/`), `dataclasses.asdict` instead of `.__dict__` for JSON serialization, `exp.Predicate` instead of `exp.Condition` for WHERE extraction, `find_all(exp.AggFunc)` instead of manual `.walk()`, and explicit alias-resolution wiring (the spec described it as "essential" but never actually showed it being called from `parse()`).
