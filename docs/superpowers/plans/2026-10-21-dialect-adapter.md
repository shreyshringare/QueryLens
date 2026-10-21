# Dialect Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `DialectAdapter`, which transpiles SQL between PostgreSQL/MySQL/SQLite/DuckDB using sqlglot, returning a structured result instead of raising, and never passes the project's canonical dialect names straight to sqlglot (which rejects `"postgresql"`).

**Architecture:** New package `src/dialect/` with `models.py` (`AdaptResult` dataclass) and `adapter.py` (`DialectAdapter` class, one public method `adapt()`). A class-level `CANONICAL_TO_SQLGLOT` dict maps the project's canonical dialect names to sqlglot's dialect keys before any sqlglot call. `adapt()` calls `sqlglot.transpile(..., unsupported_level=ErrorLevel.RAISE)` and catches `sqlglot.errors.SqlglotError` (common base of `ParseError`/`UnsupportedError`/`TokenError`, confirmed via `__mro__`), converting both success and failure into an `AdaptResult`.

**Tech Stack:** Python 3.12 (project venv at `.venv`), sqlglot 27.14.0, pytest, dataclasses. Same environment note as the Phase 2 plan: **always** use `.venv/Scripts/python.exe` (Git Bash) or `.venv\Scripts\python.exe` (PowerShell) — system Python lacks sqlglot/pytest.

**Spec:** `docs/superpowers/specs/2026-10-21-dialect-adapter-design.md`

---

## File Structure

- `src/dialect/models.py` — `AdaptResult` dataclass (new file).
- `src/dialect/adapter.py` — `DialectAdapter` class (new file).
- `src/dialect/__init__.py` — re-exports (new file).
- `tests/test_dialect_adapter.py` — all tests for this plan (new file).

---

### Task 1: AdaptResult dataclass

**Files:**
- Create: `src/dialect/models.py`
- Test: `tests/test_dialect_adapter.py` (new)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dialect_adapter.py
from src.dialect.models import AdaptResult


def test_adapt_result_holds_values():

    result = AdaptResult(
        sql="SELECT 1",
        success=True,
        error=None,
        source_dialect="postgresql",
        target_dialect="mysql",
    )

    assert result.sql == "SELECT 1"
    assert result.success is True
    assert result.error is None
    assert result.source_dialect == "postgresql"
    assert result.target_dialect == "mysql"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_dialect_adapter.py -v`
Expected: FAIL / ERROR — `ModuleNotFoundError: No module named 'src.dialect'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/dialect/models.py
from dataclasses import dataclass


@dataclass
class AdaptResult:
    sql: str | None
    success: bool
    error: str | None
    source_dialect: str
    target_dialect: str
```

Also create an empty `src/dialect/__init__.py` (no content yet — required so `src.dialect` is importable as a package; populated in Task 7).

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_dialect_adapter.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add src/dialect/models.py src/dialect/__init__.py tests/test_dialect_adapter.py
git commit -m "feat(dialect): add AdaptResult dataclass"
```

---

### Task 2: DialectAdapter — dialect name resolution

**Why first:** `sqlglot.parse_one(read="postgresql")` raises `ValueError: Unknown dialect 'postgresql'. Did you mean postgres?` (verified against sqlglot 27.14.0) — the project's canonical dialect name for PostgreSQL. Resolution must happen before any sqlglot call, and an unresolvable dialect must short-circuit without calling sqlglot at all.

**Files:**
- Create: `src/dialect/adapter.py`
- Test: `tests/test_dialect_adapter.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dialect_adapter.py  (append)
from src.dialect.adapter import DialectAdapter


def test_adapt_rejects_unknown_source_dialect():

    adapter = DialectAdapter()

    result = adapter.adapt("SELECT 1", source_dialect="oracle", target_dialect="postgresql")

    assert result.success is False
    assert result.sql is None
    assert "oracle" in result.error
    assert result.source_dialect == "oracle"
    assert result.target_dialect == "postgresql"


def test_adapt_rejects_unknown_target_dialect():

    adapter = DialectAdapter()

    result = adapter.adapt("SELECT 1", source_dialect="postgresql", target_dialect="unknown")

    assert result.success is False
    assert result.sql is None
    assert "unknown" in result.error
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_dialect_adapter.py::test_adapt_rejects_unknown_source_dialect -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.dialect.adapter'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/dialect/adapter.py
from .models import AdaptResult


class DialectAdapter:

    # Maps the project's canonical dialect names (src/data_pipeline/dialects.py
    # ::SUPPORTED_DIALECTS) to sqlglot's own dialect keys. sqlglot has no
    # "postgresql" alias and raises ValueError if given one directly — this
    # map exists specifically to prevent that crash. "unknown" (the pipeline's
    # sentinel for unrecognized dialects) is intentionally absent: any name
    # not in this map is unresolvable and short-circuits before any sqlglot call.
    CANONICAL_TO_SQLGLOT = {
        "postgresql": "postgres",
        "mysql": "mysql",
        "sqlite": "sqlite",
        "duckdb": "duckdb",
    }

    def _resolve(self, dialect: str) -> str | None:
        return self.CANONICAL_TO_SQLGLOT.get(dialect)

    def adapt(self, sql: str, source_dialect: str, target_dialect: str) -> AdaptResult:

        resolved_source = self._resolve(source_dialect)
        resolved_target = self._resolve(target_dialect)

        if resolved_source is None:
            return AdaptResult(
                sql=None,
                success=False,
                error=f"Unknown dialect: {source_dialect}",
                source_dialect=source_dialect,
                target_dialect=target_dialect,
            )

        if resolved_target is None:
            return AdaptResult(
                sql=None,
                success=False,
                error=f"Unknown dialect: {target_dialect}",
                source_dialect=source_dialect,
                target_dialect=target_dialect,
            )

        # Transpile call added in Task 3 — for now, resolution-only tests pass
        # because both failure branches above return before reaching here.
        raise NotImplementedError("transpile step added in Task 3")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_dialect_adapter.py -v`
Expected: PASS (3 tests — the 2 new ones plus Task 1's)

- [ ] **Step 5: Commit**

```bash
git add src/dialect/adapter.py tests/test_dialect_adapter.py
git commit -m "feat(dialect): resolve canonical dialect names before sqlglot calls"
```

---

### Task 3: DialectAdapter — successful transpile path

**Files:**
- Modify: `src/dialect/adapter.py`
- Test: `tests/test_dialect_adapter.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dialect_adapter.py  (append)
def test_adapt_transpiles_concat_postgresql_to_mysql():

    adapter = DialectAdapter()

    result = adapter.adapt(
        "SELECT a || b FROM t",
        source_dialect="postgresql",
        target_dialect="mysql",
    )

    assert result.success is True
    assert result.error is None
    assert result.sql == "SELECT CONCAT(a, b) FROM t"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_dialect_adapter.py::test_adapt_transpiles_concat_postgresql_to_mysql -v`
Expected: FAIL — `NotImplementedError: transpile step added in Task 3`

- [ ] **Step 3: Write minimal implementation**

```python
# src/dialect/adapter.py
import sqlglot
from sqlglot.errors import ErrorLevel

from .models import AdaptResult


class DialectAdapter:

    CANONICAL_TO_SQLGLOT = {
        "postgresql": "postgres",
        "mysql": "mysql",
        "sqlite": "sqlite",
        "duckdb": "duckdb",
    }

    def _resolve(self, dialect: str) -> str | None:
        return self.CANONICAL_TO_SQLGLOT.get(dialect)

    def adapt(self, sql: str, source_dialect: str, target_dialect: str) -> AdaptResult:

        resolved_source = self._resolve(source_dialect)
        resolved_target = self._resolve(target_dialect)

        if resolved_source is None:
            return AdaptResult(
                sql=None,
                success=False,
                error=f"Unknown dialect: {source_dialect}",
                source_dialect=source_dialect,
                target_dialect=target_dialect,
            )

        if resolved_target is None:
            return AdaptResult(
                sql=None,
                success=False,
                error=f"Unknown dialect: {target_dialect}",
                source_dialect=source_dialect,
                target_dialect=target_dialect,
            )

        # unsupported_level=RAISE: sqlglot's default silently embeds a warning
        # comment in the output SQL for unsupported constructs instead of
        # failing. RAISE converts that into a catchable UnsupportedError so a
        # broken transpile can never silently reach the execution agent.
        statements = sqlglot.transpile(
            sql,
            read=resolved_source,
            write=resolved_target,
            unsupported_level=ErrorLevel.RAISE,
        )

        return AdaptResult(
            sql="; ".join(statements),
            success=True,
            error=None,
            source_dialect=source_dialect,
            target_dialect=target_dialect,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_dialect_adapter.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/dialect/adapter.py tests/test_dialect_adapter.py
git commit -m "feat(dialect): transpile SQL via sqlglot in DialectAdapter"
```

---

### Task 4: DialectAdapter — error handling

**Why:** `sqlglot.transpile` raises on invalid SQL (`ParseError`) and, with `unsupported_level=RAISE`, on unsupported constructs (`UnsupportedError`). Both share a common base, `sqlglot.errors.SqlglotError` (verified via `__mro__` against sqlglot 27.14.0) — one `except` clause covers both. Per the design spec, `adapt()` must never raise; all failures become a failed `AdaptResult`.

**Files:**
- Modify: `src/dialect/adapter.py`
- Test: `tests/test_dialect_adapter.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dialect_adapter.py  (append)
def test_adapt_catches_invalid_sql():

    adapter = DialectAdapter()

    result = adapter.adapt(
        "SELECT FROM FROM",
        source_dialect="sqlite",
        target_dialect="postgresql",
    )

    assert result.success is False
    assert result.sql is None
    assert result.error is not None
    assert len(result.error) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_dialect_adapter.py::test_adapt_catches_invalid_sql -v`
Expected: FAIL — `sqlglot.errors.ParseError` propagates uncaught out of `adapt()`

- [ ] **Step 3: Write minimal implementation**

```python
# src/dialect/adapter.py
import sqlglot
from sqlglot.errors import ErrorLevel, SqlglotError

from .models import AdaptResult


class DialectAdapter:

    CANONICAL_TO_SQLGLOT = {
        "postgresql": "postgres",
        "mysql": "mysql",
        "sqlite": "sqlite",
        "duckdb": "duckdb",
    }

    def _resolve(self, dialect: str) -> str | None:
        return self.CANONICAL_TO_SQLGLOT.get(dialect)

    def adapt(self, sql: str, source_dialect: str, target_dialect: str) -> AdaptResult:

        resolved_source = self._resolve(source_dialect)
        resolved_target = self._resolve(target_dialect)

        if resolved_source is None:
            return AdaptResult(
                sql=None,
                success=False,
                error=f"Unknown dialect: {source_dialect}",
                source_dialect=source_dialect,
                target_dialect=target_dialect,
            )

        if resolved_target is None:
            return AdaptResult(
                sql=None,
                success=False,
                error=f"Unknown dialect: {target_dialect}",
                source_dialect=source_dialect,
                target_dialect=target_dialect,
            )

        try:
            statements = sqlglot.transpile(
                sql,
                read=resolved_source,
                write=resolved_target,
                unsupported_level=ErrorLevel.RAISE,
            )
        except SqlglotError as exc:
            return AdaptResult(
                sql=None,
                success=False,
                error=str(exc),
                source_dialect=source_dialect,
                target_dialect=target_dialect,
            )

        return AdaptResult(
            sql="; ".join(statements),
            success=True,
            error=None,
            source_dialect=source_dialect,
            target_dialect=target_dialect,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_dialect_adapter.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/dialect/adapter.py tests/test_dialect_adapter.py
git commit -m "feat(dialect): catch SqlglotError and return a failed AdaptResult"
```

---

### Task 5: Same-dialect round trip

**Why:** Per the design spec, `adapt()` always parses and regenerates, even when `source_dialect == target_dialect` — this surfaces generated-SQL syntax errors uniformly regardless of whether a dialect switch is actually needed.

**Files:**
- Modify: `tests/test_dialect_adapter.py` (test only — no production code change; this behavior already falls out of Task 4's implementation since there's no same-dialect shortcut)

- [ ] **Step 1: Write the test**

```python
# tests/test_dialect_adapter.py  (append)
def test_adapt_same_dialect_round_trip():

    adapter = DialectAdapter()

    result = adapter.adapt(
        "SELECT a, b FROM t WHERE a > 1",
        source_dialect="duckdb",
        target_dialect="duckdb",
    )

    assert result.success is True
    assert result.sql == "SELECT a, b FROM t WHERE a > 1"
```

- [ ] **Step 2: Run test to verify it passes immediately**

Run: `.venv/Scripts/python.exe -m pytest tests/test_dialect_adapter.py::test_adapt_same_dialect_round_trip -v`
Expected: PASS (no new implementation needed — confirms no same-dialect shortcut exists)

- [ ] **Step 3: Commit**

```bash
git add tests/test_dialect_adapter.py
git commit -m "test(dialect): lock in same-dialect round-trip behavior"
```

---

### Task 6: Package exports

**Files:**
- Modify: `src/dialect/__init__.py`
- Test: `tests/test_dialect_adapter.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dialect_adapter.py  (append)
def test_dialect_package_exports():
    from src.dialect import AdaptResult, DialectAdapter  # noqa: F401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_dialect_adapter.py::test_dialect_package_exports -v`
Expected: FAIL — `ImportError: cannot import name 'AdaptResult' from 'src.dialect'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/dialect/__init__.py
from .models import AdaptResult
from .adapter import DialectAdapter

__all__ = [
    "AdaptResult",
    "DialectAdapter",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_dialect_adapter.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add src/dialect/__init__.py tests/test_dialect_adapter.py
git commit -m "feat(dialect): export AdaptResult and DialectAdapter from package init"
```

---

### Task 7: 20 cross-dialect parametrized pairs

**Why:** CLAUDE.md's Phase 4 gate requires `test_dialect_adapter.py` to pass on 20 cross-dialect pairs. These 20 cases were run directly against the installed sqlglot 27.14.0 during design (not guessed) — each `(sql, source, target)` input below was executed and its `expected` is the verbatim output observed. This locks in verified-correct behavior as a regression suite; it does not test for behavior that hasn't been confirmed to exist.

**Files:**
- Modify: `tests/test_dialect_adapter.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_dialect_adapter.py  (append)
import pytest


CROSS_DIALECT_CASES = [
    # (sql, source_dialect, target_dialect, expected_sql)
    ("SELECT a || b FROM t", "postgresql", "mysql", "SELECT CONCAT(a, b) FROM t"),
    ("SELECT a || b FROM t", "sqlite", "mysql", "SELECT CONCAT(a, b) FROM t"),
    ("SELECT a || b FROM t", "duckdb", "postgresql", "SELECT a || b FROM t"),
    ("SELECT a || b FROM t", "sqlite", "duckdb", "SELECT a || b FROM t"),

    ("SELECT GROUP_CONCAT(name) FROM t", "postgresql", "mysql", "SELECT GROUP_CONCAT(name SEPARATOR ',') FROM t"),
    ("SELECT GROUP_CONCAT(name) FROM t", "postgresql", "duckdb", "SELECT LISTAGG(name, ',') FROM t"),
    ("SELECT GROUP_CONCAT(name) FROM t", "mysql", "postgresql", "SELECT STRING_AGG(name, ',') FROM t"),
    ("SELECT GROUP_CONCAT(name) FROM t", "duckdb", "sqlite", "SELECT GROUP_CONCAT(name) FROM t"),

    ("SELECT IFNULL(a, 0) FROM t", "postgresql", "mysql", "SELECT COALESCE(a, 0) FROM t"),
    ("SELECT IFNULL(a, 0) FROM t", "sqlite", "duckdb", "SELECT COALESCE(a, 0) FROM t"),
    ("SELECT IFNULL(a, 0) FROM t", "mysql", "sqlite", "SELECT COALESCE(a, 0) FROM t"),

    ("SELECT * FROM t LIMIT 5, 10", "mysql", "postgresql", "SELECT * FROM t LIMIT 10 OFFSET 5"),
    ("SELECT * FROM t LIMIT 5, 10", "mysql", "sqlite", "SELECT * FROM t LIMIT 10 OFFSET 5"),
    ("SELECT * FROM t LIMIT 10 OFFSET 5", "postgresql", "duckdb", "SELECT * FROM t LIMIT 10 OFFSET 5"),

    ("SELECT CAST(a AS INTEGER) FROM t", "postgresql", "mysql", "SELECT CAST(a AS SIGNED) FROM t"),
    ("SELECT CAST(a AS INTEGER) FROM t", "mysql", "postgresql", "SELECT CAST(a AS INT) FROM t"),
    ("SELECT CAST(a AS TEXT) FROM t", "sqlite", "mysql", "SELECT CAST(a AS CHAR) FROM t"),
    ("SELECT CAST(a AS TEXT) FROM t", "mysql", "postgresql", "SELECT CAST(a AS TEXT) FROM t"),

    ("SELECT TRUE, FALSE", "postgresql", "mysql", "SELECT TRUE, FALSE"),

    ("SELECT SUBSTR(a, 1, 3) FROM t", "mysql", "postgresql", "SELECT SUBSTRING(a FROM 1 FOR 3) FROM t"),
    ("SELECT SUBSTR(a, 1, 3) FROM t", "postgresql", "mysql", "SELECT SUBSTRING(a, 1, 3) FROM t"),

    ("SELECT IF(a > 1, 'x', 'y') FROM t", "postgresql", "sqlite", "SELECT IIF(a > 1, 'x', 'y') FROM t"),
    ("SELECT IF(a > 1, 'x', 'y') FROM t", "mysql", "duckdb", "SELECT CASE WHEN a > 1 THEN 'x' ELSE 'y' END FROM t"),
]


@pytest.mark.parametrize("sql,source,target,expected", CROSS_DIALECT_CASES)
def test_cross_dialect_transpile(sql, source, target, expected):

    adapter = DialectAdapter()

    result = adapter.adapt(sql, source_dialect=source, target_dialect=target)

    assert result.success is True
    assert result.error is None
    assert result.sql == expected
```

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_dialect_adapter.py -v`
Expected: PASS for all 23 parametrized cases — no new production code needed, since this exercises `DialectAdapter.adapt()` built in Tasks 2-4 against inputs already verified to produce these exact outputs. If any case fails, the discrepancy is between this plan's recorded probe output and the actual installed sqlglot version — stop and report the exact mismatch rather than editing the expected value to force a pass.

- [ ] **Step 3: Commit**

```bash
git add tests/test_dialect_adapter.py
git commit -m "test(dialect): add 20+ cross-dialect transpile regression cases"
```

---

### Task 8: Full suite run

**Files:** none (verification only)

- [ ] **Step 1: Run the new test file in isolation**

Run: `.venv/Scripts/python.exe -m pytest tests/test_dialect_adapter.py -v`
Expected: all tests PASS (30 total: 1 from Task 1 + 2 from Task 2 + 1 from Task 3 + 1 from Task 4 + 1 from Task 5 + 1 from Task 6 + 23 from Task 7 — confirm the exact count matches what's in the file rather than trusting this arithmetic).

- [ ] **Step 2: Confirm no regression in the rest of the suite**

Run: `.venv/Scripts/python.exe -m pytest tests/ -q 2>&1 | tail -20`
Expected: all previously-passing tests (151 before this plan) still pass, plus the new `test_dialect_adapter.py` tests — no failures anywhere else in `src/schema/` or `src/sql/`.

---

## Self-Review Notes

- **Spec coverage:** Design spec's `AdaptResult`/`DialectAdapter`/`CANONICAL_TO_SQLGLOT` → Tasks 1-4. `unsupported_level=RAISE` → Task 3. `SqlglotError` catch-all → Task 4. Same-dialect round trip → Task 5. Package exports → Task 6. 20 cross-dialect pairs test file → Task 7. "Out of scope" items (DDL adaptation, speculative fixups, execution-agent wiring) are correctly not represented by any task.
- **Placeholder scan:** every step has complete, runnable code; no TBD markers.
- **Type consistency:** `AdaptResult` fields (`sql`, `success`, `error`, `source_dialect`, `target_dialect`) and `DialectAdapter.adapt(sql, source_dialect, target_dialect)` signature are defined once in Tasks 1-2 and used identically through Task 7.
