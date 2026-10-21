# Dialect Adapter — Design Spec

**Phase:** Phase 4 of CLAUDE.md build order. Gate: `test_dialect_adapter.py` passes on 20 cross-dialect pairs.

**Goal:** Transpile SQL between PostgreSQL / MySQL / SQLite / DuckDB so generated SQL can run against the target database's dialect. Runs after SQL generation, before execution, per CLAUDE.md constraint "Dialect Adapter MUST run after generation, before execution."

## Background / verified facts

Two real, empirically-verified facts drive this design (probed against the installed `sqlglot==27.14.0` directly, not assumed):

1. **Canonical dialect name mismatch.** The project's canonical dialect names (`src/data_pipeline/dialects.py::SUPPORTED_DIALECTS`) are `postgresql`, `mysql`, `sqlite`, `duckdb`, `unknown`. sqlglot's own dialect keys are `postgres`, `mysql`, `sqlite`, `duckdb` — it has no `"postgresql"` alias and raises `ValueError: Unknown dialect 'postgresql'. Did you mean postgres?` if passed directly. Any code that passes a canonical dialect string straight to `sqlglot.parse_one(read=...)` (e.g. `scripts/build_structured_dataset.py`, `src/sql/parser.py::SQLParser`) will crash on a `postgresql`-tagged record. The adapter must map canonical → sqlglot names itself; it cannot assume the two naming schemes line up.
2. **sqlglot already transpiles correctly for the patterns that matter.** Probed all 12 directional pairs across {postgresql, mysql, sqlite, duckdb} on 15 representative SQL patterns: string concat (`||` vs `CONCAT`), `GROUP_CONCAT`/`STRING_AGG`/`LISTAGG`, `IFNULL`→`COALESCE`, MySQL-style vs standard `LIMIT`/`OFFSET`, `CAST` type names (`INTEGER`/`SIGNED`/`INT`, `TEXT`/`CHAR`), boolean literals, `IF`→`CASE`. All transpiled correctly out of the box. No hardcoded fixup table is justified by evidence — one is not included.
3. **The one real gap:** sqlglot's default `unsupported_level` lets a genuinely-unsupported construct through as an inline warning comment in the output SQL, not a raised error. Left unhandled, a broken transpile could silently reach the execution agent. Fix: pass `unsupported_level=sqlglot.ErrorLevel.RAISE` so it raises `sqlglot.errors.UnsupportedError` instead.

## Architecture

New package `src/dialect/`, mirroring the existing `src/sql` / `src/schema` package structure:

- `src/dialect/models.py` — one dataclass:
  ```python
  @dataclass
  class AdaptResult:
      sql: str | None
      success: bool
      error: str | None
      source_dialect: str
      target_dialect: str
  ```
- `src/dialect/adapter.py` — `DialectAdapter` class:
  - Class-level `CANONICAL_TO_SQLGLOT: dict[str, str]` mapping `postgresql→postgres`; `mysql`, `sqlite`, `duckdb` map to themselves. `unknown` is absent (any dialect not in the map is unresolvable).
  - `adapt(self, sql: str, source_dialect: str, target_dialect: str) -> AdaptResult`:
    1. Resolve both `source_dialect` and `target_dialect` through `CANONICAL_TO_SQLGLOT`. If either is missing, return `AdaptResult(sql=None, success=False, error="Unknown dialect: <name>", source_dialect=source_dialect, target_dialect=target_dialect)` — no sqlglot call attempted.
    2. Call `sqlglot.transpile(sql, read=<resolved source>, write=<resolved target>, unsupported_level=sqlglot.ErrorLevel.RAISE)`.
    3. On success, join the returned statement list with `"; "` (sqlglot returns a list of statements) and return `AdaptResult(sql=<result>, success=True, error=None, ...)`.
    4. On `sqlglot.errors.SqlglotError` (covers `ParseError`, `UnsupportedError`, `TokenError` — all share this common base, verified via `__mro__`), return `AdaptResult(sql=None, success=False, error=str(exc), ...)`. Never raises out of `adapt()`.
  - Same-dialect calls (`source_dialect == target_dialect`, both resolved) still go through the full parse+regenerate round trip rather than a passthrough shortcut — this uniformly surfaces generated-SQL syntax errors regardless of whether a dialect switch is actually needed, consistent with the adapter always running post-generation.
- `src/dialect/__init__.py` — re-exports `AdaptResult`, `DialectAdapter`, matching `src/sql/__init__.py`'s export pattern.

## Testing

`tests/test_dialect_adapter.py` (name matches the CLAUDE.md Phase 4 gate exactly):

- **Dialect name mapping:** `postgresql` source/target resolves and transpiles without the raw `ValueError`; `unknown` dialect returns a failed `AdaptResult` without touching sqlglot.
- **~20 parametrized cross-dialect pairs** covering the verified-correct patterns from the Background section (concat, aggregation functions, `IFNULL`, `LIMIT`/`OFFSET` styles, `CAST`, `IF`/`CASE`, boolean literals), spread across varied source→target combinations (not just postgresql→mysql repeated).
- **Failure paths:** syntactically invalid SQL input → `success=False` with a non-empty `error`; unsupported-construct case (if one can be found/constructed) → `success=False` via the `UnsupportedError` path, not a silently-broken SQL string.
- **Same-dialect round trip:** one case with `source_dialect == target_dialect`, asserting it still parses successfully and returns semantically equivalent SQL.

## Out of scope

- No DDL dialect adaptation (CREATE TABLE / AUTO_INCREMENT / SERIAL differences) — the adapter operates on generated query SQL (SELECT-shaped), not schema DDL.
- No semantic fixups beyond what sqlglot already does correctly (see verified fact #2). If real-world generation/eval later surfaces an actual mistranspilation, it gets added then, with a regression test proving the specific failure — not speculatively now.
- No integration wiring into an execution/self-healing agent yet — that agent doesn't exist in the codebase (Phase 8 in CLAUDE.md's build order, not yet built). This phase delivers the adapter as a standalone, tested unit.
