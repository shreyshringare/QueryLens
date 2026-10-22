# SQL Validator Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `SQLSchemaValidator.validate()` to cross-check `.joins`, `.filters`, `.aggregations`, and `.group_by` column references against the schema — currently only `.tables` and `.select_columns` are checked (see the scope-limiting comment at `src/schema/validator.py:76-79`).

**Architecture:** Extract the existing `select_columns`-checking logic (skip unqualified columns, skip CTE-qualified columns, else check `schema.has_column`) into a private helper `_check_column`, then call it for every `ColumnReference` across the newly-covered clauses. `join.table`'s own existence is already covered by the existing `.tables` check (verified: the parser's `_extract_tables` walks every `exp.Table` node regardless of clause) — no new table-level check needed. `.order_by` stays out of scope (unstructured text, not a `ColumnReference`).

**Tech Stack:** Python 3.11 (project venv at `.venv`), pytest. No new dependencies. Same environment note as prior plans: **always** use `.venv/Scripts/python.exe` (Git Bash) or `.venv\Scripts\python.exe` (PowerShell).

**Spec:** `docs/superpowers/specs/2026-10-22-sql-validator-hardening-design.md`

**Already done (do not redo):** `SQLSchemaValidator`'s table/select_columns checking, CTE-name skip logic, case-insensitive `has_column` — all already exist in `src/schema/validator.py` and are tested by the 7 existing tests in `tests/test_schema_validator.py` (verified by actually running `pytest tests/test_schema_validator.py -v` before writing this plan — collected 7 items, not 6). Do not modify any of those 7 existing tests or the `_build_shop_schema()` fixture they use.

---

## File Structure

- `src/schema/validator.py` — modify `SQLSchemaValidator` only (`SchemaValidator` class, `src/sql/parser.py`, `src/sql/models.py`, `src/schema/models.py` are NOT touched by this plan).
- `tests/test_schema_validator.py` — append new tests only; a new fixture helper `_build_shop_schema_with_orders()` is added alongside the existing `_build_shop_schema()` (which stays untouched).

---

### Task 1: Extract `_check_column` helper (pure refactor, no behavior change)

**Why no new test first:** this task changes HOW the existing `select_columns` check is implemented, not WHAT it does — the 7 existing tests are the safety net. There's no new behavior to write a failing test for.

**Files:**
- Modify: `src/schema/validator.py`

- [ ] **Step 1: Run the existing tests to confirm a clean baseline**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_validator.py -v`
Expected: PASS (7 tests) — confirms the starting point before refactoring.

- [ ] **Step 2: Refactor**

Replace the entire contents of `src/schema/validator.py` with:

```python
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
```

**Note:** `SchemaValidator` is reproduced byte-for-byte unchanged above — only `SQLSchemaValidator` actually changes (the inline `select_columns` loop body is replaced by a call to the new `_check_column` helper; behavior is identical, just restructured).

- [ ] **Step 3: Run tests to verify no regression**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_validator.py -v`
Expected: PASS (7 tests, same as before the refactor — no new tests yet, no behavior change)

- [ ] **Step 4: Commit**

```bash
git add src/schema/validator.py
git commit -m "refactor(schema): extract _check_column helper from SQLSchemaValidator.validate"
```

---

### Task 2: Validate join columns

**Files:**
- Modify: `src/schema/validator.py`
- Test: `tests/test_schema_validator.py`

- [ ] **Step 1: Write the failing test**

First, READ the current full contents of `tests/test_schema_validator.py` (it currently has 6 tests plus `_build_shop_schema()`). Then APPEND this at the end — do NOT remove or alter any existing content:

```python
from src.sql.models import Join


def _build_shop_schema_with_orders():

    customer_id = Column(name="customer_id", data_type="INTEGER", primary_key=True)
    name_col = Column(name="name", data_type="TEXT")
    customers = Table(name="customers", columns=[customer_id, name_col])

    order_id = Column(name="order_id", data_type="INTEGER", primary_key=True)
    order_customer_id = Column(name="customer_id", data_type="INTEGER")
    amount = Column(name="amount", data_type="DECIMAL")
    orders = Table(name="orders", columns=[order_id, order_customer_id, amount])

    return DatabaseSchema(database_id="shop", tables=[customers, orders])


def test_sql_schema_validator_flags_unknown_column_in_join():

    schema = _build_shop_schema_with_orders()

    structure = SQLStructure(
        tables=["customers", "orders"],
        joins=[
            Join(
                join_type="JOIN",
                table="orders",
                left=ColumnReference(table="customers", column="customer_id"),
                right=ColumnReference(table="orders", column="customer_name"),
            )
        ],
    )

    validator = SQLSchemaValidator(schema)

    errors = validator.validate(structure)

    assert errors == ["Unknown column: orders.customer_name"]
```

(`customers.customer_id` on the `left` side is a real column, so only the `right` side's `orders.customer_name` — which doesn't exist, only `orders.customer_id` does — produces an error. This single test proves both sides of a join are actually checked, not just one.)

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_validator.py::test_sql_schema_validator_flags_unknown_column_in_join -v`
Expected: FAIL — `assert [] == ["Unknown column: orders.customer_name"]` (joins aren't checked yet)

- [ ] **Step 3: Write minimal implementation**

In `src/schema/validator.py`, add the join-checking loop to `SQLSchemaValidator.validate()`, right after the `select_columns` loop:

```python
        for reference in sql_structure.select_columns:
            self._check_column(reference, cte_names, errors)

        for join in sql_structure.joins:
            self._check_column(join.left, cte_names, errors)
            self._check_column(join.right, cte_names, errors)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_validator.py -v`
Expected: PASS (8 tests — 7 existing + 1 new test function containing the assertion, but note this task also added the `_build_shop_schema_with_orders` helper which isn't a test itself; confirm the actual test COUNT, not the line count)

- [ ] **Step 5: Commit**

```bash
git add src/schema/validator.py tests/test_schema_validator.py
git commit -m "feat(schema): validate join column references in SQLSchemaValidator"
```

---

### Task 3: Validate filter columns

**Files:**
- Modify: `src/schema/validator.py`
- Test: `tests/test_schema_validator.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_schema_validator.py`:

```python
from src.sql.models import Filter


def test_sql_schema_validator_flags_unknown_column_in_filter():

    schema = _build_shop_schema()

    structure = SQLStructure(
        tables=["customers"],
        filters=[
            Filter(
                column=ColumnReference(table="customers", column="unknown_col"),
                operator="EQ",
                value="customers.unknown_col = 1",
            )
        ],
    )

    validator = SQLSchemaValidator(schema)

    errors = validator.validate(structure)

    assert errors == ["Unknown column: customers.unknown_col"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_validator.py::test_sql_schema_validator_flags_unknown_column_in_filter -v`
Expected: FAIL — `assert [] == ["Unknown column: customers.unknown_col"]`

- [ ] **Step 3: Write minimal implementation**

In `src/schema/validator.py`, add the filter-checking loop right after the joins loop:

```python
        for join in sql_structure.joins:
            self._check_column(join.left, cte_names, errors)
            self._check_column(join.right, cte_names, errors)

        for filter_ in sql_structure.filters:
            self._check_column(filter_.column, cte_names, errors)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_validator.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add src/schema/validator.py tests/test_schema_validator.py
git commit -m "feat(schema): validate filter column references in SQLSchemaValidator"
```

---

### Task 4: Validate aggregation columns (and skip `None`)

**Files:**
- Modify: `src/schema/validator.py`
- Test: `tests/test_schema_validator.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_schema_validator.py`:

```python
from src.sql.models import Aggregation


def test_sql_schema_validator_flags_unknown_column_in_aggregation():

    schema = _build_shop_schema()

    structure = SQLStructure(
        tables=["customers"],
        aggregations=[
            Aggregation(function="SUM", column=ColumnReference(table="customers", column="unknown_col")),
        ],
    )

    validator = SQLSchemaValidator(schema)

    errors = validator.validate(structure)

    assert errors == ["Unknown column: customers.unknown_col"]


def test_sql_schema_validator_skips_aggregation_with_no_column():

    schema = _build_shop_schema()

    structure = SQLStructure(
        tables=["customers"],
        aggregations=[
            Aggregation(function="COUNT", column=None),
        ],
    )

    validator = SQLSchemaValidator(schema)

    errors = validator.validate(structure)

    assert errors == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_validator.py::test_sql_schema_validator_flags_unknown_column_in_aggregation -v`
Expected: FAIL — `assert [] == ["Unknown column: customers.unknown_col"]`

(`test_sql_schema_validator_skips_aggregation_with_no_column` will pass immediately even before the implementation — aggregations aren't checked at all yet, so a `None` column trivially produces no error either way. That's fine; it still needs to pass AFTER the change too, which Step 4 confirms — the real risk this test guards against is a future implementation forgetting the `column is None` guard and crashing with `AttributeError` on `None.table`.)

- [ ] **Step 3: Write minimal implementation**

In `src/schema/validator.py`, add the aggregation-checking loop right after the filters loop:

```python
        for filter_ in sql_structure.filters:
            self._check_column(filter_.column, cte_names, errors)

        for aggregation in sql_structure.aggregations:
            if aggregation.column is not None:
                self._check_column(aggregation.column, cte_names, errors)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_validator.py -v`
Expected: PASS (11 tests)

- [ ] **Step 5: Commit**

```bash
git add src/schema/validator.py tests/test_schema_validator.py
git commit -m "feat(schema): validate aggregation column references in SQLSchemaValidator"
```

---

### Task 5: Validate group_by columns

**Files:**
- Modify: `src/schema/validator.py`
- Test: `tests/test_schema_validator.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_schema_validator.py`:

```python
def test_sql_schema_validator_flags_unknown_column_in_group_by():

    schema = _build_shop_schema()

    structure = SQLStructure(
        tables=["customers"],
        group_by=[ColumnReference(table="customers", column="unknown_col")],
    )

    validator = SQLSchemaValidator(schema)

    errors = validator.validate(structure)

    assert errors == ["Unknown column: customers.unknown_col"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_validator.py::test_sql_schema_validator_flags_unknown_column_in_group_by -v`
Expected: FAIL — `assert [] == ["Unknown column: customers.unknown_col"]`

- [ ] **Step 3: Write minimal implementation**

In `src/schema/validator.py`, add the group_by-checking loop right after the aggregations loop, and update the trailing scope comment to reflect the now-wider (but still not full) coverage:

```python
        for aggregation in sql_structure.aggregations:
            if aggregation.column is not None:
                self._check_column(aggregation.column, cte_names, errors)

        for reference in sql_structure.group_by:
            self._check_column(reference, cte_names, errors)

        # .tables, .select_columns, .joins, .filters, .aggregations, and
        # .group_by are all cross-checked against the schema. .order_by is
        # NOT validated here — OrderBy.expression is a rendered SQL text
        # string (e.g. from sqlglot's .sql()), not a structured
        # ColumnReference, so checking it would require re-parsing that
        # string rather than reusing _check_column; out of scope for now.
        return errors
```

(This replaces the old `# Only .tables and .select_columns are cross-checked...` comment and the bare `return errors` that followed it.)

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_validator.py -v`
Expected: PASS (12 tests)

- [ ] **Step 5: Commit**

```bash
git add src/schema/validator.py tests/test_schema_validator.py
git commit -m "feat(schema): validate group_by column references in SQLSchemaValidator"
```

---

### Task 6: CTE-skip regression test for the new call sites

**Why:** Task 1's `_check_column` helper is shared across every clause, so the CTE-skip behavior should automatically apply everywhere — but this needs a test, not just an assumption, since joins/filters are new call sites that didn't exist when the original CTE-skip test (`test_sql_schema_validator_skips_columns_qualified_by_cte`, covering only `select_columns`) was written.

**Files:**
- Test: `tests/test_schema_validator.py` (test-only, no production code change expected)

- [ ] **Step 1: Write the test**

Append to `tests/test_schema_validator.py`:

```python
def test_sql_schema_validator_skips_cte_qualified_columns_in_filters_and_joins():

    schema = _build_shop_schema()

    structure = SQLStructure(
        tables=[],
        cte_names=["recent"],
        filters=[
            Filter(
                column=ColumnReference(table="recent", column="total"),
                operator="GT",
                value="recent.total > 100",
            )
        ],
        joins=[
            Join(
                join_type="JOIN",
                table="customers",
                left=ColumnReference(table="recent", column="customer_id"),
                right=ColumnReference(table="customers", column="customer_id"),
            )
        ],
    )

    validator = SQLSchemaValidator(schema)

    errors = validator.validate(structure)

    assert errors == []
```

(`recent.total` and `recent.customer_id` are CTE-qualified and skipped; `customers.customer_id` on the join's `right` side is a real column — so the expected result is no errors at all.)

- [ ] **Step 2: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_validator.py::test_sql_schema_validator_skips_cte_qualified_columns_in_filters_and_joins -v`
Expected: PASS immediately — no new implementation needed, since Task 1's shared `_check_column` helper already applies the CTE-skip check uniformly to every call site added in Tasks 2-5. If this test FAILS, that means the CTE-skip logic did NOT actually get reused correctly somewhere — stop and report the exact failure rather than adding special-case logic to force a pass.

- [ ] **Step 3: Commit**

```bash
git add tests/test_schema_validator.py
git commit -m "test(schema): confirm CTE-qualified columns are skipped in joins and filters too"
```

---

### Task 7: Full valid-structure integration test

**Files:**
- Modify: `src/schema/validator.py` (comment-only touch-up, see note below — may already be complete after Task 5)
- Test: `tests/test_schema_validator.py`

- [ ] **Step 1: Write the test**

Append to `tests/test_schema_validator.py`:

```python
def test_sql_schema_validator_passes_with_valid_joins_filters_aggregations_group_by():

    schema = _build_shop_schema_with_orders()

    structure = SQLStructure(
        tables=["customers", "orders"],
        select_columns=[ColumnReference(table="customers", column="name")],
        joins=[
            Join(
                join_type="JOIN",
                table="orders",
                left=ColumnReference(table="customers", column="customer_id"),
                right=ColumnReference(table="orders", column="customer_id"),
            )
        ],
        filters=[
            Filter(
                column=ColumnReference(table="orders", column="amount"),
                operator="GT",
                value="orders.amount > 100",
            ),
        ],
        aggregations=[
            Aggregation(function="SUM", column=ColumnReference(table="orders", column="amount")),
        ],
        group_by=[ColumnReference(table="customers", column="name")],
    )

    validator = SQLSchemaValidator(schema)

    errors = validator.validate(structure)

    assert errors == []
```

- [ ] **Step 2: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_validator.py -v`
Expected: PASS (14 tests). This test should already pass given Tasks 1-5's implementation — every column referenced (`customers.name`, `customers.customer_id`, `orders.customer_id`, `orders.amount`) genuinely exists in `_build_shop_schema_with_orders()`. If it fails, there's a real bug in one of the prior tasks' implementations — stop and report, don't patch around it here.

- [ ] **Step 3: Confirm the trailing scope comment from Task 5 is accurate**

Re-read the final `src/schema/validator.py` and confirm the comment above `return errors` correctly lists all six now-checked clauses (tables, select_columns, joins, filters, aggregations, group_by) and still correctly notes `.order_by` is out of scope. If Task 5 already added this comment correctly, no further change is needed here — this step is a verification, not necessarily a new edit.

- [ ] **Step 4: Commit**

```bash
git add tests/test_schema_validator.py
git commit -m "test(schema): add integration test with valid joins, filters, aggregations, and group_by"
```

---

### Task 8: Full suite run

**Files:** none (verification only)

- [ ] **Step 1: Run the validator test file in isolation**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_validator.py -v`
Expected: all 14 tests PASS (7 original + 1 join + 1 filter + 2 aggregation + 1 group_by + 1 CTE-regression + 1 integration — confirm the exact count matches what's in the file rather than trusting this arithmetic).

- [ ] **Step 2: Confirm no regression in the rest of the suite**

Run: `.venv/Scripts/python.exe -m pytest tests/ -q 2>&1 | tail -20`
Expected: all previously-passing tests (190 before this plan) still pass, plus the new tests in `test_schema_validator.py` — no failures anywhere else in `src/sql/`, `src/dialect/`, or `src/agents/`.

---

## Self-Review Notes

- **Spec coverage:** design spec's `_check_column` extraction, join/filter/aggregation/group_by coverage, `.order_by` out-of-scope note → Tasks 1-5. CTE-skip regression for new call sites → Task 6. Full valid-structure integration test → Task 7. "Out of scope" items (`.order_by` validation, parser/model changes, semantic/type validation) are correctly not represented by any task.
- **Placeholder scan:** every step has complete, runnable code; no TBD markers.
- **Type consistency:** `_check_column(reference, cte_names, errors)` signature defined once in Task 1, used identically for every clause in Tasks 2-5. `SQLSchemaValidator.validate(sql_structure)` signature unchanged throughout.
- **Fixture isolation:** the 6 pre-existing tests and `_build_shop_schema()` are never modified by any task in this plan — all new tests either reuse `_build_shop_schema()` unchanged or use the new, separate `_build_shop_schema_with_orders()` fixture introduced in Task 2. This avoids any risk of accidentally changing behavior for already-passing tests.
