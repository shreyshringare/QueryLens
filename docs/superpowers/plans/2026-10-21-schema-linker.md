# Schema Linker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `SchemaLinker`, which uses a pretrained `sentence-transformers` cross-encoder to rank every column in a `DatabaseSchema` by relevance to an NL question, and prune a schema down to the top-k relevant columns (plus each selected table's primary/foreign keys, to preserve joinability).

**Architecture:** New package `src/agents/` with `schema_linker.py` (`ColumnScore` dataclass + `SchemaLinker` class: `rank()` and `select()`) and `evaluation.py` (`recall_at_k()` helper). `rank()` builds one candidate string per column (`"{table}.{column} ({data_type})"`), scores all of them against the question in one `CrossEncoder.predict()` batch call, sorts descending. `select()` calls `rank()`, takes the top-k, then widens the result to include each selected table's primary key and foreign key columns (verified necessary — see Task 4).

**Tech Stack:** Python 3.11 (project venv at `.venv`), `sentence-transformers==6.2.0` (pulls in `torch`), pretrained model `cross-encoder/ms-marco-MiniLM-L6-v2` (~90MB, downloaded once into the HF cache on first use), pytest. Same environment note as prior plans: **always** use `.venv/Scripts/python.exe` (Git Bash) or `.venv\Scripts\python.exe` (PowerShell).

**Spec:** `docs/superpowers/specs/2026-10-21-schema-linker-design.md`

**Already done (do not redo):** `sentence-transformers==6.2.0` is already installed in `.venv` and added to `requirements.txt`. `src/schema/models.py` (`Column`, `Table`, `ForeignKey`, `DatabaseSchema`) already exists and is NOT modified by this plan — only imported.

**Important — every expected value in this plan was verified by actually running the installed model before being written down, not guessed.** If any assertion fails when you run it, STOP and report the exact mismatch — do not edit the expected value to force a pass (same discipline as the Dialect Adapter plan's Task 7, where a real transcription error was correctly caught this way).

---

## File Structure

- `src/agents/schema_linker.py` — `ColumnScore` dataclass, `SchemaLinker` class (new package/file).
- `src/agents/evaluation.py` — `recall_at_k()` function (new file).
- `src/agents/__init__.py` — re-exports (new file).
- `tests/test_schema_linker.py` — all tests for this plan (new file).

---

### Task 1: ColumnScore dataclass + SchemaLinker model loading

**Files:**
- Create: `src/agents/schema_linker.py`
- Test: `tests/test_schema_linker.py` (new)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_schema_linker.py
from sentence_transformers import CrossEncoder

from src.agents.schema_linker import ColumnScore, SchemaLinker


def test_column_score_holds_values():

    score = ColumnScore(table="customers", column="name", score=-1.5)

    assert score.table == "customers"
    assert score.column == "name"
    assert score.score == -1.5


def test_schema_linker_loads_default_model():

    linker = SchemaLinker()

    assert isinstance(linker.model, CrossEncoder)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_linker.py -v`
Expected: FAIL / ERROR — `ModuleNotFoundError: No module named 'src.agents'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/agents/schema_linker.py
from dataclasses import dataclass

from sentence_transformers import CrossEncoder


@dataclass
class ColumnScore:
    table: str
    column: str
    score: float


class SchemaLinker:

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L6-v2"):
        self.model = CrossEncoder(model_name)
```

Also create an empty `src/agents/__init__.py` (populated in Task 5).

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_linker.py -v`
Expected: PASS (2 tests). This loads the real model from the local HF cache (already downloaded during design) — expect a few seconds, not instant, but no network download needed if the cache is warm. If it tries to download and there's no network, report BLOCKED — don't fake/skip this.

- [ ] **Step 5: Commit**

```bash
git add src/agents/schema_linker.py src/agents/__init__.py tests/test_schema_linker.py
git commit -m "feat(agents): add ColumnScore and SchemaLinker model loading"
```

---

### Task 2: SchemaLinker.rank()

**Why this exact test data:** this is the real `ecommerce` schema and a real question from `data/structured/structured.jsonl` record id `"0"`. The expected top-3 was verified by actually running `cross-encoder/ms-marco-MiniLM-L6-v2` against all 13 columns of this exact schema with this exact question before writing this task — output was (sorted descending): `customers.country (TEXT)` -2.26, `customers.name (TEXT)` -5.55, `customers.customer_id (INT)` -6.09, `orders.customer_id (INT)` -8.21, `products.name (TEXT)` -10.33, ... (10 more, all lower). This also happens to exactly match the real ground-truth SQL for this question (`SELECT customer_id, name FROM customers WHERE country = 'India'`).

**Files:**
- Modify: `src/agents/schema_linker.py`
- Test: `tests/test_schema_linker.py`

- [ ] **Step 1: Write the failing test**

Append this test, and the schema-fixture helper it depends on, to `tests/test_schema_linker.py` (this fixture will be reused by every later task in this plan — build it once here):

```python
# tests/test_schema_linker.py  (append)
from src.schema.models import Column, DatabaseSchema, ForeignKey, Table


def _ecommerce_schema() -> DatabaseSchema:

    customers = Table(
        name="customers",
        columns=[
            Column(name="customer_id", data_type="INT", primary_key=True),
            Column(name="name", data_type="TEXT"),
            Column(name="country", data_type="TEXT"),
        ],
    )
    products = Table(
        name="products",
        columns=[
            Column(name="product_id", data_type="INT", primary_key=True),
            Column(name="name", data_type="TEXT"),
            Column(name="category", data_type="TEXT"),
            Column(name="price", data_type="DOUBLE"),
        ],
    )
    orders = Table(
        name="orders",
        columns=[
            Column(name="order_id", data_type="INT", primary_key=True),
            Column(name="customer_id", data_type="INT"),
            Column(name="order_date", data_type="DATE"),
        ],
        foreign_keys=[
            ForeignKey(column="customer_id", referenced_table="customers", referenced_column="customer_id"),
        ],
    )
    order_items = Table(
        name="order_items",
        columns=[
            Column(name="order_id", data_type="INT"),
            Column(name="product_id", data_type="INT"),
            Column(name="quantity", data_type="INT"),
        ],
        foreign_keys=[
            ForeignKey(column="order_id", referenced_table="orders", referenced_column="order_id"),
            ForeignKey(column="product_id", referenced_table="products", referenced_column="product_id"),
        ],
    )

    return DatabaseSchema(
        database_id="ecommerce",
        tables=[customers, products, orders, order_items],
    )


# Model loaded once at module scope — the ~1-3s load cost is paid once for the
# whole test file, not once per test.
_LINKER = SchemaLinker()


def test_rank_orders_all_columns_by_relevance():

    schema = _ecommerce_schema()

    results = _LINKER.rank("Which customers are from India?", schema)

    assert len(results) == 13

    top_3 = {(r.table, r.column) for r in results[:3]}
    assert top_3 == {
        ("customers", "country"),
        ("customers", "name"),
        ("customers", "customer_id"),
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_linker.py::test_rank_orders_all_columns_by_relevance -v`
Expected: FAIL — `AttributeError: 'SchemaLinker' object has no attribute 'rank'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/agents/schema_linker.py
from dataclasses import dataclass

from sentence_transformers import CrossEncoder

from src.schema.models import DatabaseSchema


@dataclass
class ColumnScore:
    table: str
    column: str
    score: float


class SchemaLinker:

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L6-v2"):
        self.model = CrossEncoder(model_name)

    def rank(self, question: str, schema: DatabaseSchema) -> list[ColumnScore]:

        candidates = []
        locations = []

        for table in schema.tables:
            for column in table.columns:
                candidates.append(f"{table.name}.{column.name} ({column.data_type})")
                locations.append((table.name, column.name))

        scores = self.model.predict([(question, candidate) for candidate in candidates])

        results = [
            ColumnScore(table=table_name, column=column_name, score=float(score))
            for (table_name, column_name), score in zip(locations, scores)
        ]

        results.sort(key=lambda item: item.score, reverse=True)

        return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_linker.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/agents/schema_linker.py tests/test_schema_linker.py
git commit -m "feat(agents): rank schema columns by relevance to a question"
```

---

### Task 3: SchemaLinker.select() — top-k pruning, no join-key augmentation yet

**Why this exact test data:** real question from record id `"4"` (`"Which customers have spent more than 500 dollars?"`). Verified by running the model against all 13 columns of the same schema: top-5 (descending) is `customers.country` -8.69, `customers.customer_id` -8.76, `customers.name` -9.00, `orders.customer_id` -9.91, `products.price` -10.56. Note this naturally selects all 3 `customers` columns, but only 1 column each from `orders` (`customer_id`, not the primary key `order_id`) and `products` (`price`, not the primary key `product_id`) — this is intentional and sets up Task 4, which proves the join-key augmentation actually changes behavior.

**Files:**
- Modify: `src/agents/schema_linker.py`
- Test: `tests/test_schema_linker.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_schema_linker.py  (append)
def test_select_prunes_to_top_k_columns_and_their_tables():

    schema = _ecommerce_schema()

    pruned = _LINKER.select(
        "Which customers have spent more than 500 dollars?",
        schema,
        top_k=5,
    )

    table_names = {table.name for table in pruned.tables}
    assert table_names == {"customers", "orders", "products"}

    orders_table = pruned.get_table("orders")
    assert {column.name for column in orders_table.columns} == {"customer_id"}

    products_table = pruned.get_table("products")
    assert {column.name for column in products_table.columns} == {"price"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_linker.py::test_select_prunes_to_top_k_columns_and_their_tables -v`
Expected: FAIL — `AttributeError: 'SchemaLinker' object has no attribute 'select'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/agents/schema_linker.py
from dataclasses import dataclass

from sentence_transformers import CrossEncoder

from src.schema.models import DatabaseSchema, Table


@dataclass
class ColumnScore:
    table: str
    column: str
    score: float


class SchemaLinker:

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L6-v2"):
        self.model = CrossEncoder(model_name)

    def rank(self, question: str, schema: DatabaseSchema) -> list[ColumnScore]:

        candidates = []
        locations = []

        for table in schema.tables:
            for column in table.columns:
                candidates.append(f"{table.name}.{column.name} ({column.data_type})")
                locations.append((table.name, column.name))

        scores = self.model.predict([(question, candidate) for candidate in candidates])

        results = [
            ColumnScore(table=table_name, column=column_name, score=float(score))
            for (table_name, column_name), score in zip(locations, scores)
        ]

        results.sort(key=lambda item: item.score, reverse=True)

        return results

    def select(self, question: str, schema: DatabaseSchema, top_k: int = 3) -> DatabaseSchema:

        top = self.rank(question, schema)[:top_k]

        selected_columns: dict[str, set[str]] = {}

        for item in top:
            selected_columns.setdefault(item.table, set()).add(item.column)

        pruned_tables = []

        for table in schema.tables:

            if table.name not in selected_columns:
                continue

            kept_names = selected_columns[table.name]
            kept_columns = [column for column in table.columns if column.name in kept_names]

            pruned_tables.append(Table(name=table.name, columns=kept_columns, foreign_keys=[]))

        return DatabaseSchema(database_id=schema.database_id, tables=pruned_tables)
```

Note: `foreign_keys=[]` here is a known, intentional gap closed in Task 4 — join-key preservation isn't implemented yet.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_linker.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/agents/schema_linker.py tests/test_schema_linker.py
git commit -m "feat(agents): prune schema to top-k ranked columns in SchemaLinker.select"
```

---

### Task 4: SchemaLinker.select() — primary/foreign key augmentation

**Why:** per the design spec, a selected table's primary key and foreign key columns must survive pruning even if the cross-encoder didn't rank them in the top-k — otherwise `SQLSchemaValidator` (already built) would flag false "unknown column" errors on an otherwise-valid join once a real SQL generator tries to reference them. Task 3's test already proves this matters: without augmentation, the pruned `orders` table has only `customer_id` (missing its primary key `order_id`), and `products` has only `price` (missing its primary key `product_id`).

**Why this second test case:** real question from record id `"3"` (`"How many orders has each customer placed?"`). Verified by running the model against all 13 columns: top-1 (highest score) is `orders.customer_id` at -2.36. At `top_k=1`, only `orders` is a selected table, and only `customer_id` is naturally selected — `orders.order_id` (primary key) is NOT in the natural top-1, so this is a clean, independent confirmation that augmentation is doing real work (not just coincidentally matching Task 3's case).

**Files:**
- Modify: `src/agents/schema_linker.py`
- Test: `tests/test_schema_linker.py`

- [ ] **Step 1: Update the existing test and add a new one**

Update `test_select_prunes_to_top_k_columns_and_their_tables` (from Task 3) in place — the `orders` and `products` assertions change now that primary keys are included:

```python
# tests/test_schema_linker.py  (update in place)
def test_select_prunes_to_top_k_columns_and_their_tables():

    schema = _ecommerce_schema()

    pruned = _LINKER.select(
        "Which customers have spent more than 500 dollars?",
        schema,
        top_k=5,
    )

    table_names = {table.name for table in pruned.tables}
    assert table_names == {"customers", "orders", "products"}

    orders_table = pruned.get_table("orders")
    assert {column.name for column in orders_table.columns} == {"customer_id", "order_id"}

    products_table = pruned.get_table("products")
    assert {column.name for column in products_table.columns} == {"price", "product_id"}
```

Then append this new test:

```python
# tests/test_schema_linker.py  (append)
def test_select_includes_primary_key_even_when_not_top_ranked():

    schema = _ecommerce_schema()

    pruned = _LINKER.select(
        "How many orders has each customer placed?",
        schema,
        top_k=1,
    )

    assert {table.name for table in pruned.tables} == {"orders"}

    orders_table = pruned.get_table("orders")
    assert {column.name for column in orders_table.columns} == {"customer_id", "order_id"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_linker.py -v`
Expected: FAIL on both the updated test (now expects `order_id`/`product_id` that aren't produced yet) and the new test.

- [ ] **Step 3: Write minimal implementation**

```python
# src/agents/schema_linker.py
from dataclasses import dataclass

from sentence_transformers import CrossEncoder

from src.schema.models import DatabaseSchema, Table


@dataclass
class ColumnScore:
    table: str
    column: str
    score: float


class SchemaLinker:

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L6-v2"):
        self.model = CrossEncoder(model_name)

    def rank(self, question: str, schema: DatabaseSchema) -> list[ColumnScore]:

        candidates = []
        locations = []

        for table in schema.tables:
            for column in table.columns:
                candidates.append(f"{table.name}.{column.name} ({column.data_type})")
                locations.append((table.name, column.name))

        scores = self.model.predict([(question, candidate) for candidate in candidates])

        results = [
            ColumnScore(table=table_name, column=column_name, score=float(score))
            for (table_name, column_name), score in zip(locations, scores)
        ]

        results.sort(key=lambda item: item.score, reverse=True)

        return results

    def select(self, question: str, schema: DatabaseSchema, top_k: int = 3) -> DatabaseSchema:

        top = self.rank(question, schema)[:top_k]

        selected_columns: dict[str, set[str]] = {}

        for item in top:
            selected_columns.setdefault(item.table, set()).add(item.column)

        # Auto-include primary/foreign keys of every selected table, even if the
        # cross-encoder didn't rank them in the top-k — otherwise a pruned-away
        # FK/PK column would make SQLSchemaValidator flag false "unknown column"
        # errors on an otherwise-valid join once SQL referencing it is generated.
        for table in schema.tables:

            if table.name not in selected_columns:
                continue

            for column in table.columns:
                if column.primary_key:
                    selected_columns[table.name].add(column.name)

            for foreign_key in table.foreign_keys:
                selected_columns[table.name].add(foreign_key.column)

        pruned_tables = []

        for table in schema.tables:

            if table.name not in selected_columns:
                continue

            kept_names = selected_columns[table.name]
            kept_columns = [column for column in table.columns if column.name in kept_names]
            kept_foreign_keys = [fk for fk in table.foreign_keys if fk.column in kept_names]

            pruned_tables.append(
                Table(name=table.name, columns=kept_columns, foreign_keys=kept_foreign_keys)
            )

        return DatabaseSchema(database_id=schema.database_id, tables=pruned_tables)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_linker.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/agents/schema_linker.py tests/test_schema_linker.py
git commit -m "feat(agents): preserve primary/foreign keys of selected tables in SchemaLinker.select"
```

---

### Task 5: Package exports

**Files:**
- Modify: `src/agents/__init__.py`
- Test: `tests/test_schema_linker.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_schema_linker.py  (append)
def test_agents_package_exports():
    from src.agents import ColumnScore, SchemaLinker  # noqa: F401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_linker.py::test_agents_package_exports -v`
Expected: FAIL — `ImportError: cannot import name 'ColumnScore' from 'src.agents'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/agents/__init__.py
from .schema_linker import ColumnScore, SchemaLinker

__all__ = [
    "ColumnScore",
    "SchemaLinker",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_linker.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add src/agents/__init__.py tests/test_schema_linker.py
git commit -m "feat(agents): export ColumnScore and SchemaLinker from package init"
```

---

### Task 6: recall_at_k() evaluation helper

**Why this exact test data:** trivial, verified case — question `"What is the user's email address?"` against a 2-column `users` table (`email`, `age`). Running the model gives `users.email` a score of 0.17 and `users.age` a score of -5.12, so `email` is unambiguously top-1. This makes the test deterministic without needing to probe a large schema — it tests `recall_at_k`'s own arithmetic (does it correctly compute a fraction across mixed hit/miss cases), not the model's real-world recall rate (that's Task 7's job).

**Files:**
- Create: `src/agents/evaluation.py`
- Test: `tests/test_schema_linker.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_schema_linker.py  (append)
from src.agents.evaluation import recall_at_k


def _users_schema() -> DatabaseSchema:

    users = Table(
        name="users",
        columns=[
            Column(name="email", data_type="TEXT"),
            Column(name="age", data_type="INT"),
        ],
    )

    return DatabaseSchema(database_id="demo", tables=[users])


def test_recall_at_k_computes_fraction_of_fully_covered_cases():

    schema = _users_schema()
    question = "What is the user's email address?"

    cases = [
        (schema, question, [("users", "email")]),  # hits @ top_k=1
        (schema, question, [("users", "age")]),     # misses @ top_k=1
    ]

    fraction = recall_at_k(cases, _LINKER, top_k=1)

    assert fraction == 0.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_linker.py::test_recall_at_k_computes_fraction_of_fully_covered_cases -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.agents.evaluation'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/agents/evaluation.py
from src.schema.models import DatabaseSchema

from .schema_linker import SchemaLinker


def recall_at_k(
    cases: list[tuple[DatabaseSchema, str, list[tuple[str, str]]]],
    linker: SchemaLinker,
    top_k: int,
) -> float:

    if not cases:
        return 0.0

    hits = 0

    for schema, question, ground_truth in cases:

        ranked = linker.rank(question, schema)
        top = {(item.table, item.column) for item in ranked[:top_k]}

        if all(pair in top for pair in ground_truth):
            hits += 1

    return hits / len(cases)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_linker.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add src/agents/evaluation.py tests/test_schema_linker.py
git commit -m "feat(agents): add recall_at_k evaluation helper"
```

---

### Task 7: Real-data recall@3 smoke test

**Why:** CLAUDE.md's Phase 2 gate text is "top-3 columns hit ground-truth columns on 80%+ of val set." This task measures the REAL fraction on the 6 real records in `data/structured/structured.jsonl` (all share the same `ecommerce` schema already built as `_ecommerce_schema()`). **The measured result, verified by actually running `recall_at_k` against the installed model before writing this task, is 3/6 = 0.5 — not 80%.** This is reported honestly per CLAUDE.md's "NEVER fabricate numbers" rule. The gap is expected: this is a zero-shot pretrained model with no training (`agents/train_schema_linker.py` from CLAUDE.md's command list is a separate, not-yet-built step), evaluated against only 6 records (nowhere near "a val set" at dataset scale — `data/build_schema_linker_dataset.py`, also not yet built, is Phase 1 data-generation scope). This test exists to catch regressions in the linking pipeline, not to assert the gate is met.

**Ground truth per record** (derived from each record's own `sql_structure` in `data/structured/structured.jsonl`, resolving `"table": null` entries to the record's single listed table where unambiguous):

| id | question | ground truth columns |
|----|----------|----------------------|
| 0 | Which customers are from India? | customers.customer_id, customers.name, customers.country |
| 1 | What is the average product price? | products.price |
| 2 | Which products cost more than 100 dollars? | products.name, products.price |
| 3 | How many orders has each customer placed? | orders.customer_id |
| 4 | Which customers have spent more than 500 dollars? | orders.customer_id, orders.order_id, order_items.order_id, order_items.product_id, products.product_id, order_items.quantity, products.price |
| 5 | Which products have never been ordered? | products.product_id, products.name, order_items.product_id |

**Files:**
- Modify: `tests/test_schema_linker.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_schema_linker.py  (append)
def test_recall_at_3_on_real_structured_dataset_records():

    schema = _ecommerce_schema()

    cases = [
        (
            schema,
            "Which customers are from India?",
            [("customers", "customer_id"), ("customers", "name"), ("customers", "country")],
        ),
        (
            schema,
            "What is the average product price?",
            [("products", "price")],
        ),
        (
            schema,
            "Which products cost more than 100 dollars?",
            [("products", "name"), ("products", "price")],
        ),
        (
            schema,
            "How many orders has each customer placed?",
            [("orders", "customer_id")],
        ),
        (
            schema,
            "Which customers have spent more than 500 dollars?",
            [
                ("orders", "customer_id"),
                ("orders", "order_id"),
                ("order_items", "order_id"),
                ("order_items", "product_id"),
                ("products", "product_id"),
                ("order_items", "quantity"),
                ("products", "price"),
            ],
        ),
        (
            schema,
            "Which products have never been ordered?",
            [("products", "product_id"), ("products", "name"), ("order_items", "product_id")],
        ),
    ]

    fraction = recall_at_k(cases, _LINKER, top_k=3)

    # Measured, not asserted-to-be-80%: 3 of 6 real records have all their
    # ground-truth columns inside the top-3 ranked columns (records 0, 1, 3
    # hit; records 2, 4, 5 miss — record 4 in particular needs 7 ground-truth
    # columns across 3 tables, impossible to fully cover at top_k=3). This is
    # expected for a zero-shot, untrained model on 6 records — see the Task 7
    # docstring-equivalent note in the plan for why this isn't the CLAUDE.md
    # gate being claimed as met.
    assert fraction == 3 / 6
```

- [ ] **Step 2: Run test to verify it passes (or report the real discrepancy)**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_linker.py::test_recall_at_3_on_real_structured_dataset_records -v`
Expected: PASS, with `fraction == 0.5`. If the actual fraction differs from `3/6`, STOP — do not edit the assertion to force a pass. Report BLOCKED with the exact fraction observed and which specific cases flipped hit/miss compared to this plan's table above (this would mean a real discrepancy between the plan's verified-at-design-time model output and the installed model, needing human judgment — same discipline as the Dialect Adapter plan's Task 7).

- [ ] **Step 3: Commit**

```bash
git add tests/test_schema_linker.py
git commit -m "test(agents): measure recall@3 on real structured dataset records"
```

---

### Task 8: Full suite run

**Files:** none (verification only)

- [ ] **Step 1: Run the new test file in isolation**

Run: `.venv/Scripts/python.exe -m pytest tests/test_schema_linker.py -v`
Expected: all 8 tests PASS (1 from Task 1's `test_column_score_holds_values` + 1 from Task 1's `test_schema_linker_loads_default_model` + 1 from Task 2 + 1 from Task 3/4's updated test + 1 new from Task 4 + 1 from Task 5 + 1 from Task 6 + 1 from Task 7 — confirm the exact count matches what's in the file rather than trusting this arithmetic).

- [ ] **Step 2: Confirm no regression in the rest of the suite**

Run: `.venv/Scripts/python.exe -m pytest tests/ -q 2>&1 | tail -20`
Expected: all previously-passing tests (181 before this plan) still pass, plus the new `test_schema_linker.py` tests — no failures anywhere else in `src/schema/`, `src/sql/`, or `src/dialect/`.

---

## Self-Review Notes

- **Spec coverage:** Design spec's `ColumnScore`/`SchemaLinker.rank`/`SchemaLinker.select` (with PK/FK augmentation) → Tasks 1-4. Package exports → Task 5. `recall_at_k` → Task 6. Real-data honest measurement (not a fabricated 80% claim) → Task 7. "Out of scope" items (training, dataset-scale eval, GPU/ANN optimization, generation-pipeline integration, confidence calibration) are correctly not represented by any task.
- **Placeholder scan:** every step has complete, runnable code; no TBD markers.
- **Type consistency:** `ColumnScore(table, column, score)` and `SchemaLinker.rank(question, schema)` / `.select(question, schema, top_k)` signatures are defined once in Task 1-4 and used identically through Task 7. `recall_at_k(cases, linker, top_k)` defined in Task 6, used unchanged in Task 7.
- **Empirical grounding:** every expected value (Task 2's top-3, Task 3/4's top-5 and top-1 column sets, Task 6's email/age scores, Task 7's 3/6 fraction and per-record ground truth) was computed by actually running `cross-encoder/ms-marco-MiniLM-L6-v2` against the real data before being written into this plan — not estimated or guessed.
