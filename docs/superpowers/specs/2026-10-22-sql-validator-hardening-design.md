# SQL Validator Hardening — Design Spec

**Phase:** Phase 3 of CLAUDE.md build order (hardening pass — `SQLSchemaValidator` itself was already built during Phase 2). Gate (stated): "test_sql_validator.py passes; catches hallucinated table names" — already true today for tables and `select_columns`; this phase closes the remaining documented gap.

**Goal:** `SQLSchemaValidator.validate()` currently only cross-checks `sql_structure.tables` and `sql_structure.select_columns` against the schema — `.joins`, `.filters`, `.aggregations`, and `.group_by` are explicitly unchecked (see the comment at `src/schema/validator.py:76-79`, written during Phase 2 as a known, deliberate scope limit for a follow-up task — this is that follow-up). This phase extends validation to those four clauses.

## Background / verified facts

1. **The CTE-qualified-column gap mentioned in old Phase 2 plan notes is already fixed**, not part of this phase's scope. `SQLStructure.cte_names` (`src/sql/models.py:47`) is populated by the parser (`src/sql/parser.py:37-45`) and `SQLSchemaValidator.validate()` already skips any `ColumnReference` whose table matches a CTE name (`src/schema/validator.py:64-69`, tested by `test_sql_schema_validator_skips_columns_qualified_by_cte`). Confirmed by reading both files directly before writing this spec — no code change needed here.
2. **`join.table`'s existence is already covered.** `src/sql/parser.py::_extract_tables` walks every `exp.Table` node in the parse tree via `expression.find_all(exp.Table)` regardless of which clause it appears in (FROM, JOIN, etc.), so a table that only appears in a JOIN clause is still present in `sql_structure.tables` and already caught by the existing table-existence loop. No new table-level check is needed for joins — only the `Join.left`/`Join.right` column references need checking.
3. **`OrderBy` stores unstructured text, not a `ColumnReference`.** `OrderBy.expression` (`src/sql/models.py:32-34`) is `item.this.sql()` — a rendered SQL expression string (could be a column, a function call, an ordinal number, etc.), not a structured `(table, column)` pair. Validating it would require re-parsing that string with sqlglot, a meaningfully different and separate piece of work. `.order_by` stays explicitly out of scope for this phase, same as today.

## Architecture

Modify `src/schema/validator.py`'s `SQLSchemaValidator` only — no changes to `src/sql/parser.py`, `src/sql/models.py`, or `src/schema/models.py`.

- Extract the existing inline `select_columns` validation logic into a private helper:
  ```python
  def _check_column(self, reference: ColumnReference, cte_names: set[str], errors: list[str]) -> None:

      if reference.table is None:
          return

      if reference.table.lower() in cte_names:
          return

      if not self.schema.has_column(reference.table, reference.column):
          errors.append(f"Unknown column: {reference.table}.{reference.column}")
  ```
  (Exact skip semantics — unqualified columns silently skipped, CTE-qualified columns silently skipped — are unchanged from today's `select_columns` behavior, just reused.)
- `validate()` calls `_check_column` for:
  - every `ColumnReference` in `select_columns` (unchanged behavior, now routed through the helper)
  - both `join.left` and `join.right` for every `Join` in `joins`
  - `filter_.column` for every `Filter` in `filters`
  - `aggregation.column` for every `Aggregation` in `aggregations`, skipping entries where `column is None` (e.g. `COUNT(*)` has no column)
  - every `ColumnReference` in `group_by`
- Order of checks in `validate()`: tables → select_columns → joins → filters → aggregations → group_by (matches the order fields are declared in `SQLStructure`, and matters for exact-list-equality assertions in tests).
- `.order_by` remains unchecked — add a one-line comment updating the existing "only tables and select_columns are checked" note to accurately describe the new, still-partial scope (tables, select_columns, joins, filters, aggregations, group_by — not order_by).

## Testing

`tests/test_schema_validator.py` (existing file, append new tests, don't modify the 6 existing ones):
- One test per newly-checked clause, each with a schema that has a genuine unknown-column error in exactly that clause and nothing else: `joins` (bad column on `left`, then a separate case for `right`, or one case covering both sides), `filters`, `aggregations` (with a non-`None` column), `group_by`.
- One test confirming `aggregations` entries with `column=None` (e.g. `COUNT(*)`) don't crash and produce no error.
- One test confirming a CTE-qualified column inside a `filter` or `join` (not just `select_columns`) is still correctly skipped — proves the extracted `_check_column` helper didn't regress the CTE-skip behavior for the new call sites.
- One "everything valid" integration-style test exercising a structure with populated joins/filters/aggregations/group_by, all referencing real columns, asserting `errors == []`.

## Out of scope

- `.order_by` validation (would require re-parsing `OrderBy.expression` text — separate task).
- Any change to `src/sql/parser.py` or `SQLStructure` — this phase only touches the validator.
- Deeper semantic validation (type-checking filter operators against column types, aggregation-function/type compatibility, etc.) — this phase is existence-checking only, matching the existing `SQLSchemaValidator` design's scope (it has never done type-checking).
