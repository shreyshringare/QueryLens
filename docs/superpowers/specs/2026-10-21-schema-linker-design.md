# Schema Linker — Design Spec

**Phase:** Phase 2 of CLAUDE.md build order. Gate (stated): "top-3 columns hit ground-truth columns on 80%+ of val set."

**Goal:** Given an NL question and a `DatabaseSchema` (already parsed from DDL by `src/schema/parser.py`), rank every column by relevance to the question, and produce a pruned `DatabaseSchema` containing only the top-k relevant columns (plus each selected table's primary/foreign keys, to preserve joinability). This is the "Schema-linking agent prunes any DDL to relevant columns" step from the README, run before SQL generation.

## Background / verified facts

1. **Model works correctly on real project data, verified empirically before writing any code.** Loaded `cross-encoder/ms-marco-MiniLM-L6-v2` (pretrained, ~90MB, no training) via `sentence_transformers.CrossEncoder`, scored the question `"Which customers are from India?"` against 6 candidate columns formatted as `"{table}.{column} ({data_type})"`. Result, sorted by score descending:
   ```
   -1.09   customers.country (VARCHAR)
   -5.59   customers.name (VARCHAR)
   -6.66   customers.customer_id (INTEGER)
   -10.47  products.category (VARCHAR)
   -10.71  orders.order_date (DATE)
   -10.92  products.product_id (INTEGER)
   ```
   Top-3 is exactly `{customers.country, customers.name, customers.customer_id}` — which matches the real ground-truth SQL for this question (`SELECT customer_id, name FROM customers WHERE country = 'India'`) exactly: both `SELECT` columns and the `WHERE` column are in the top-3. This is the actual real record from `data/structured/structured.jsonl`, not a hand-picked example.
2. **Scores are raw, unnormalized logits** (can be negative, no fixed range) — fine for ranking/top-k selection, which is all this phase needs. Not usable as a calibrated confidence/probability without further work (out of scope here — Phase 9's confidence calibrator is a separate, later concern).
3. **`sentence-transformers` was not previously installed** in `.venv` — installed now (`sentence-transformers==6.2.0`, pulling in `torch==2.14.1` and other deps), added to `requirements.txt`. This matches CLAUDE.md's declared stack (`sentence-transformers` is listed there) — not a new/speculative dependency.

## Architecture

New package `src/agents/` — the first "agent" in the codebase, matching the directory name CLAUDE.md's build order and command list (`agents/train_schema_linker.py`, `agents/train_confidence_calibrator.py`) already reserve, though this phase does inference only, no training script.

- `src/agents/schema_linker.py`:
  - `ColumnScore` dataclass: `table: str`, `column: str`, `score: float`.
  - `SchemaLinker` class:
    - `__init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L6-v2")` — loads `CrossEncoder(model_name)` once, stored on `self.model`.
    - `rank(self, question: str, schema: DatabaseSchema) -> list[ColumnScore]` — builds one candidate string per column across every table (`f"{table.name}.{column.name} ({column.data_type})"`), scores all of them in one `model.predict([(question, c) for c in candidates])` batch call, returns `ColumnScore` entries sorted by score descending.
    - `select(self, question: str, schema: DatabaseSchema, top_k: int = 3) -> DatabaseSchema` — calls `rank()`, takes the top-k `ColumnScore` entries, determines the set of tables they belong to, then builds a new `DatabaseSchema` containing only those tables, each containing: the selected columns for that table from the top-k, PLUS every column where `column.primary_key` is `True` for that table, PLUS every column referenced by that table's `ForeignKey.column` entries (so a selected table's own FK columns survive pruning even if the cross-encoder didn't rank them in the top-k) — this preserves join integrity, which is standard practice in schema-linking literature (e.g. RESDSQL) and necessary because a pruned-away FK column would make `SQLSchemaValidator` (already built) flag false "unknown column" errors on an otherwise-valid join.
- `src/agents/__init__.py` — re-exports `ColumnScore`, `SchemaLinker`.
- `src/agents/evaluation.py`:
  - `recall_at_k(cases: list[tuple[DatabaseSchema, str, list[tuple[str, str]]]], linker: SchemaLinker, top_k: int) -> float` — for each `(schema, question, ground_truth_columns)` case, calls `linker.rank(question, schema)`, takes the top-k `(table, column)` pairs, and checks whether every ground-truth pair is present. Returns the fraction of cases where this holds (0.0 to 1.0). This is the mechanism the CLAUDE.md gate needs; see "Out of scope" below for why no 80% number is claimed yet.

## Testing

`tests/test_schema_linker.py`:
- Model loaded once at module scope (`_LINKER = SchemaLinker()`) so the ~1-3s model load cost is paid once per test run, not once per test — consistent with keeping the real-model-no-mocking approach (matches the project's established style of testing against real library behavior, e.g. the Dialect Adapter's real `sqlglot` calls) without making the suite slow.
- `rank()` test: the exact 6-column, 3-table scenario from the Background section — asserts the top-3 ranked columns are `{customers.country, customers.name, customers.customer_id}` (order not strictly pinned beyond "these three are the top 3," since exact logit ordering among near-ties isn't the contract — only top-k set membership is).
- `select()` tests:
  - A case where the top-k naturally includes a table's primary key already (sanity case).
  - A case specifically constructed so a table's FK/PK column would NOT make the natural top-k on relevance alone, asserting `select()` still includes it (proves the join-preservation logic actually does something, not just a no-op).
  - A case with a question whose relevant columns span 2 tables, asserting the pruned schema contains exactly those 2 tables, not all tables in the input schema.
- `recall_at_k()` test: a small hand-built fixture of 2-3 cases with known ground truth, asserting the function returns the correct fraction (e.g. 2/3) — this tests the *function's correctness*, not the model's real-world recall rate.
- One real-data smoke test against the actual 6 records in `data/structured/structured.jsonl` (using their already-parsed `schema` + `sql_structure.tables`/`select_columns`/`filters` as ground truth), reporting the real observed recall@3 fraction on those 6 records as a code comment/assertion-adjacent note — **not asserted as exactly 80%+** (6 records is not a statistically meaningful sample for that gate; if the real fraction is e.g. 5/6, the test asserts `>= 5/6` or just prints/logs it, it does not hardcode a claim beyond what's actually measured).

## Out of scope

- No training of a schema-linking model (`agents/train_schema_linker.py` from CLAUDE.md's command list) — this phase uses a pretrained, off-the-shelf cross-encoder, zero-shot.
- No claim about hitting the CLAUDE.md Phase 2 gate's literal "80%+ of val set" number — that requires a dataset-scale (not 6-record) labeled validation set, which is Phase 1 data-generation scope (`data/build_schema_linker_dataset.py` from CLAUDE.md's command list, not yet built), not this task.
- No GPU/batching optimization — the target schemas (per CLAUDE.md: "9 schemas across 7 domains") are small (a handful of tables/columns each), so a single CPU-side `model.predict()` batch call per question is sufficient; no ANN index, no embedding cache.
- No integration into a generation pipeline — there is no SFT/GRPO-trained model yet to feed the pruned schema into (Phase 5+ in CLAUDE.md's roadmap).
- No confidence calibration of the raw cross-encoder scores — Phase 9's concern, separate component.
