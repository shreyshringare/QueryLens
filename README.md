# QueryLens

**QueryLens** is a modular, database-agnostic Text-to-SQL data and evaluation pipeline. It ingests heterogeneous Text-to-SQL datasets such as **Spider, BIRD, and Synthetic**, normalizes them into a common representation, extracts structured database schemas and SQL structure, and prepares the data for later schema-linking and SQL-generation stages.

> **Current status:** Phase 1 (Dataset Ingestion & Normalization) and Phase 2 (Schema Understanding, SQL Representation, Schema↔SQL Validation) are complete. A pretrained, zero-shot Schema Linker (cross-encoder re-ranking) and a sqlglot-based Dialect Adapter (PostgreSQL/MySQL/SQLite/DuckDB transpilation) have been added. `SQLSchemaValidator` hardening (joins/filters/aggregations/group_by column checks) is in progress. No SQL-generation model has been trained yet — schema linking and dialect adaptation currently run against pretrained/deterministic components only.

---

## 1. Project Objective

The long-term goal of QueryLens is to build a general-purpose Text-to-SQL pipeline:

```text
Natural Language Question
          +
Database Schema
          ↓
     Schema Understanding
          ↓
     Schema Linking
          ↓
      SQL Generation
          ↓
    SQL Validation / Repair
          ↓
       Final SQL
```

The project is designed to work across **general SQL domains and multiple database dialects**, rather than being restricted to a single domain such as ecommerce.

---

# 2. Current Architecture

```text
                    ┌──────────────┐
                    │    Spider    │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │     BIRD     │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  Synthetic   │
                    └──────┬───────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ Dataset Adapters│
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │   Normalizer    │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ Unified Dataset │
                  └────────┬────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
       Schema Extraction          SQL Parsing
              │                         │
              ▼                         ▼
       Database Schema           SQL Structure
              │                         │
              └────────────┬────────────┘
                           ▼
                    Schema Linking
                           │
                           ▼
                 Text-to-SQL Pipeline
```

---

# 3. Project Phases

## Phase 1 — Dataset Ingestion & Normalization

Phase 1 converts heterogeneous datasets into a common format.

```text
Spider ──────┐
             │
BIRD ────────┼──→ Adapters → Normalizer
             │                    │
Synthetic ───┘                    ↓
                           Unified Records
                                  ↓
                           Validation
                                  ↓
                           Deduplication
                                  ↓
                           Dataset Splits
```

### Phase 1 responsibilities

* Load raw JSON/JSONL datasets
* Support multiple source formats
* Adapt source-specific fields
* Normalize questions
* Normalize SQL
* Preserve DDL
* Preserve database IDs
* Preserve dialect information
* Preserve domain metadata
* Validate records
* Remove duplicates
* Generate train/validation/test datasets
* Generate dataset statistics

---

# 4. Normalized Record Format

Every source is converted to the same logical structure:

```python
NormalizedQuery(
    id=...,
    source=...,
    domain=...,
    dialect=...,
    database_id=...,
    nl_question=...,
    ground_truth_sql=...,
    ddl=...,
    metadata=...
)
```

Example:

```json
{
  "id": "spider_000001",
  "source": "spider",
  "domain": "general",
  "dialect": "sqlite",
  "database_id": "concert_singer",
  "nl_question": "How many singers are there?",
  "ground_truth_sql": "SELECT COUNT(*) FROM singer",
  "ddl": "CREATE TABLE singer (...)",
  "metadata": {}
}
```

The important design principle is:

> Downstream components should not need to know whether a record originally came from Spider, BIRD, or Synthetic.

---

# 5. Dataset Adapters

Each dataset can have a different format.

Therefore QueryLens uses adapters:

```text
src/data_pipeline/adapters/
├── __init__.py
├── spider.py
├── bird.py
└── synthetic.py
```

The architecture is:

```text
Raw Spider Record
       ↓
SpiderAdapter
       ↓
Common Dictionary
       ↓
QueryNormalizer
       ↓
NormalizedQuery
```

The same pattern applies to BIRD and Synthetic.

This prevents dataset-specific logic from spreading throughout the rest of the codebase.

---

# 6. Phase 2 — Schema Understanding & SQL Representation

Phase 2 transforms raw DDL and SQL strings into structured representations.

```text
Normalized Record
       │
       ├──────────────┐
       │              │
       ▼              ▼
      DDL             SQL
       │              │
       ▼              ▼
 Schema Parser    SQL Parser
       │              │
       ▼              ▼
DatabaseSchema   SQL Structure
       │              │
       └───────┬──────┘
               ▼
        Schema Linking
```

---

# 7. Structured Database Schema

Instead of treating DDL as an opaque string, QueryLens extracts:

```text
Database
│
├── Tables
│   ├── Columns
│   ├── Data Types
│   └── Primary Keys
│
└── Foreign Keys
```

For example:

```text
customers
├── customer_id INTEGER PK
├── name VARCHAR
└── email VARCHAR

orders
├── order_id INTEGER PK
├── customer_id INTEGER FK
└── amount DECIMAL
```

Relationship:

```text
orders.customer_id
        │
        ▼
customers.customer_id
```

---

# 8. Schema Representation

The internal representation contains:

```python
@dataclass
class Column:
    name: str
    data_type: str
    nullable: bool = True
    primary_key: bool = False
```

```python
@dataclass
class ForeignKey:
    column: str
    referenced_table: str
    referenced_column: str
```

```python
@dataclass
class Table:
    name: str
    columns: list[Column]
    foreign_keys: list[ForeignKey]
```

```python
@dataclass
class DatabaseSchema:
    database_id: str
    tables: list[Table]
```

---

# 9. SQL Representation

SQL is also converted from a plain string into a structured representation.

For example:

```sql
SELECT c.name, COUNT(o.order_id)
FROM customers c
JOIN orders o
    ON c.customer_id = o.customer_id
WHERE o.amount > 1000
GROUP BY c.name
ORDER BY COUNT(o.order_id) DESC;
```

can be represented conceptually as:

```text
SELECT
    customers.name
    COUNT(orders.order_id)

FROM
    customers

JOIN
    orders

ON
    customers.customer_id = orders.customer_id

WHERE
    orders.amount > 1000

GROUP BY
    customers.name

ORDER BY
    COUNT(orders.order_id) DESC
```

This makes SQL structure available to later components.

---

# 10. Schema Linking

Schema linking connects the natural-language question and SQL to the relevant database schema.

For example:

```text
Question:

"How many orders did John place?"
```

Relevant schema:

```text
customers.name
customers.customer_id
orders.customer_id
orders.order_id
```

Relationship:

```text
customers
    │
    │ customer_id
    ▼
orders
```

The eventual goal is:

```text
Question
   ↓
Relevant tables
   ↓
Relevant columns
   ↓
Relevant relationships
   ↓
Relevant sub-schema
```

This will be a major component of the later phases.

## 10.1 Schema Linker (implemented)

Schema linking is implemented as `src/agents/schema_linker.py::SchemaLinker`, using a pretrained `sentence-transformers` cross-encoder (`cross-encoder/ms-marco-MiniLM-L6-v2`) — zero-shot, no training performed or required for this component:

```text
Question + DatabaseSchema
          ↓
  Score every column
  (cross-encoder re-ranking)
          ↓
     Take top-k columns
          ↓
  Add each selected table's
  primary/foreign keys back
  (preserves join integrity)
          ↓
    Pruned DatabaseSchema
```

Measured recall@3 (does the top-3 ranked columns fully cover the ground-truth columns for a question) on the 6 real labeled records currently available in `data/structured/structured.jsonl` is **3/6 (50%)** — reported honestly, not rounded up. This is expected for a zero-shot, untrained model evaluated against only 6 records; it is well short of a dataset-scale validation set. A trained schema linker (`agents/train_schema_linker.py`) and a larger labeled dataset (`data/build_schema_linker_dataset.py`) are not yet built.

## 10.2 Dialect Adapter (implemented)

`src/dialect/adapter.py::DialectAdapter` transpiles SQL between PostgreSQL, MySQL, SQLite, and DuckDB using `sqlglot`:

```text
SQL + source dialect + target dialect
          ↓
   Map canonical dialect name
   → sqlglot dialect key
   (sqlglot has no "postgresql"
    alias — only "postgres")
          ↓
     sqlglot.transpile(...)
          ↓
  AdaptResult(sql, success, error)
  — never raises; failures
    (unknown dialect, invalid
    SQL, unsupported construct)
    become a failed result
```

No hardcoded dialect-quirk fixup table — an empirical probe across all 4 dialects found `sqlglot` already transpiles concat/`GROUP_CONCAT`/`STRING_AGG`/`LISTAGG`/`IFNULL`/`LIMIT`-`OFFSET`/`CAST`/`IF`-`CASE` correctly out of the box; fixups are added only if a real failure is found, not speculatively.

---

# 11. Project Structure

The actual current structure (verified against the repo, not aspirational):

```text
QueryLens/
│
├── data/
│   ├── raw/
│   │   └── synthetic/
│   ├── schemas/
│   ├── processed/
│   └── structured/
│
├── src/
│   │
│   ├── data_pipeline/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── schema.py
│   │   ├── models.py
│   │   ├── loaders.py
│   │   ├── normalizer.py
│   │   ├── validation.py
│   │   ├── dedup.py
│   │   ├── split.py
│   │   ├── stats.py
│   │   ├── dialects.py
│   │   ├── adapt.py
│   │   ├── pipeline.py
│   │   │
│   │   └── adapters/
│   │       ├── __init__.py
│   │       ├── spider.py
│   │       ├── bird.py
│   │       └── synthetic.py
│   │
│   ├── schema/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── parser.py
│   │   ├── relationships.py
│   │   ├── relationship_graph.py
│   │   ├── serializer.py
│   │   └── validator.py          # SchemaValidator + SQLSchemaValidator
│   │
│   ├── sql/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── parser.py              # SQLParser (tables/joins/filters/aggs/group by/order by/limit)
│   │   └── aliases.py             # AliasResolver
│   │
│   ├── dialect/
│   │   ├── __init__.py
│   │   ├── models.py              # AdaptResult
│   │   └── adapter.py             # DialectAdapter
│   │
│   └── agents/
│       ├── __init__.py
│       ├── schema_linker.py       # ColumnScore, SchemaLinker
│       └── evaluation.py          # recall_at_k
│
├── scripts/
│   ├── test_loader.py
│   ├── test_spider_normalization.py
│   ├── create_synthetic_db.py
│   ├── build_normalized_dataset.py
│   └── build_structured_dataset.py
│
├── tests/
│   ├── test_spark_pipeline.py
│   ├── test_normalizer.py
│   ├── test_spider_adapter.py
│   ├── test_bird_adapter.py
│   ├── test_synthetic_adapter.py
│   ├── test_validation.py
│   ├── test_dedup.py
│   ├── test_dialects.py
│   ├── test_split.py
│   ├── test_schema_parser.py
│   ├── test_schema_relationships.py
│   ├── test_schema_validator.py
│   ├── test_sql_parser.py
│   ├── test_dialect_adapter.py
│   ├── test_schema_linker.py
│   ├── test_build_structured_dataset.py
│   ├── test_pipeline_integration.py
│   └── test_phase2_integration.py
│
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

# 12. Data Flow

## Raw ingestion

```text
data/raw/
```

contains the original datasets.

Never modify the original files.

---

## Normalization

```text
Raw Dataset
    ↓
Adapter
    ↓
Normalizer
    ↓
NormalizedQuery
```

Output:

```text
data/normalized/normalized.jsonl
```

---

## Validation

Each record is checked for:

* Question
* SQL
* Database ID
* Dialect
* DDL
* Valid metadata

Invalid records are rejected or reported.

---

## Deduplication

Duplicate examples are removed before dataset splitting.

```text
Normalized
    ↓
Deduplicate
    ↓
Clean Dataset
```

This helps prevent data leakage.

---

# 13. Dataset Splitting

After normalization and deduplication:

```text
Clean Dataset
      ↓
 ┌────┼────┐
 ▼    ▼    ▼
Train Val Test
```

Initial target:

```text
Train       80%
Validation  10%
Test        10%
```

For serious Text-to-SQL evaluation, database-level splitting should eventually be considered so that test databases can be unseen during training.

---

# 14. SQL Dialects

QueryLens is designed to be **database/dialect-aware**, not tied to one database.

The architecture can support:

```text
SQLite
MySQL
PostgreSQL
DuckDB
...
```

Dialect information is retained rather than discarded during normalization.

Example:

```json
{
  "dialect": "postgresql"
}
```

The system should not assume that every SQL statement is valid for every database engine.

---

# 15. General Domain

QueryLens is **not restricted to ecommerce**.

The `domain` field is metadata.

Possible domains include:

```text
general
ecommerce
finance
healthcare
education
retail
logistics
social_media
```

A record can simply use:

```json
{
  "domain": "general"
}
```

when a more specific domain isn't known.

The architecture should therefore remain:

```text
General Domain
       ↓
Multiple Databases
       ↓
Multiple SQL Dialects
       ↓
Text-to-SQL
```

---

# 16. Technology Stack

Current/target technologies include:

```text
Python
PySpark
pytest
JSON / JSONL
SQL
Dataclasses
```

Potential later components may include:

```text
SQL parser
Database execution engines
ML/LLM models
Vector/semantic retrieval
```

These should only be introduced when required by the corresponding project phase.

---

# 17. Testing

The project uses `pytest`.

Run all tests:

```bash
pytest -q
```

Run a specific test:

```bash
pytest tests/test_normalizer.py -q
```

Run the Spark pipeline test:

```bash
pytest tests/test_spark_pipeline.py -q
```

---

# 18. Phase 1 Completion Criteria

Phase 1 is complete when:

```text
✓ Spider can be loaded
✓ BIRD can be loaded
✓ Synthetic data can be loaded
✓ Dataset-specific formats are adapted
✓ Records are normalized
✓ Required fields are validated
✓ Duplicates are removed
✓ Dialects are preserved
✓ DDL is preserved
✓ Train/validation/test datasets are generated
✓ Dataset statistics are generated
✓ Integration tests pass
```

---

# 19. Phase 2 Completion Criteria

Phase 2 is complete when:

```text
✓ DDL can be parsed
✓ Tables can be extracted
✓ Columns can be extracted
✓ Data types are preserved
✓ Primary keys are extracted
✓ Foreign keys are extracted
✓ Relationships are represented
✓ Database schemas can be serialized
✓ SQL can be parsed
✓ SELECT/FROM/JOIN/WHERE are represented
✓ GROUP BY/HAVING are represented
✓ ORDER BY/LIMIT are represented
✓ SQL table references are extracted
✓ SQL column references are extracted
✓ SQL joins are extracted
✓ SQL aggregations are extracted
✓ SQL can be linked to the database schema
✓ Invalid schema references can be detected
✓ Phase-2 integration tests pass
```

---

# 20. Roadmap

```text
                    QueryLens
                        │
        ┌───────────────┴────────────────┐
        │                                │
     PHASE 1                          PHASE 2
 Data Engineering                Schema Understanding
        │                                │
        ▼                                ▼
 Dataset Loading                  DDL Parsing
        │                         Schema Extraction
        ▼                         SQL Parsing
 Dataset Adapters                SQL Representation
        │                         Schema Linking
        ▼                                │
 Normalization                           │
        │                                │
        ▼                                │
 Validation                              │
        │                                │
        ▼                                │
 Deduplication                           │
        │                                │
        └───────────────┬────────────────┘
                        ▼
                    PHASE 3
              Schema Linking &
              Query Understanding
                        │
                        ▼
                    PHASE 4
                SQL Generation
                        │
                        ▼
                    PHASE 5
              SQL Validation &
                    Repair
                        │
                        ▼
                    PHASE 6
                Evaluation &
                  Benchmarking
```

---

# 21. Development Philosophy

QueryLens follows several principles:

### 1. Dataset agnostic

Spider/BIRD/Synthetic-specific logic stays inside adapters.

### 2. Domain agnostic

The system should work with general SQL databases rather than one application domain.

### 3. Dialect aware

SQL dialect information is retained throughout the pipeline.

### 4. Modular

Each stage should have a clear responsibility:

```text
Loader
Adapter
Normalizer
Validator
Schema Parser
SQL Parser
Schema Linker
Generator
Evaluator
```

### 5. Test driven

Every major transformation should have unit and integration tests.

### 6. Preserve raw information

Normalization should standardize fields without unnecessarily destroying source-specific metadata.

---

# 22. Current Development Status

```text
PHASE 1
────────────────────────────────────
Dataset loading              ✅
Spark pipeline               ✅
Synthetic loading            ✅
Loader tests                 ✅
Normalization                ✅
Spider adapter               ✅
BIRD adapter                 ✅
Deduplication                ✅
Dataset splitting            ✅
Quality statistics           ✅


PHASE 2
────────────────────────────────────
Schema models                ✅
DDL parser                   ✅
Table extraction             ✅
Column extraction            ✅
Key extraction               ✅
Relationship graph           ✅
SQL parser                   ✅
SQL structure                ✅
Schema↔SQL validation         🔨  tables + select_columns done; joins/filters/aggregations/group_by in progress
Integration                  ✅


SCHEMA LINKING (zero-shot, no training)
────────────────────────────────────
Cross-encoder ranking          ✅
Top-k pruning + PK/FK keep     ✅
recall@k eval helper           ✅
Honest recall@3 on 6 records   ✅  measured 3/6 (50%), not yet the 80% gate target
Trained linker                 ⏳  agents/train_schema_linker.py not built
Dataset-scale val set          ⏳  data/build_schema_linker_dataset.py not built


DIALECT ADAPTER
────────────────────────────────────
PG/MySQL/SQLite/DuckDB transpile ✅
Canonical→sqlglot name mapping   ✅
Error handling (never raises)    ✅
23 verified cross-dialect cases  ✅


NOT STARTED
────────────────────────────────────
SFT / GRPO training            ⏳
Self-healing execution agent   ⏳
Confidence calibrator          ⏳
MCP server                     ⏳
OpenTelemetry tracing          ⏳
Held-out evaluation            ⏳
```

---

# 23. Running the Project

After installing dependencies:

```bash
pip install -r requirements.txt
```

Run tests:

```bash
pytest -q
```

Run the data loader:

```bash
python scripts/test_loader.py
```

Build the normalized dataset:

```bash
python scripts/build_normalized_dataset.py
```

Build the structured Phase-2 dataset:

```bash
python scripts/build_structured_dataset.py
```

---

# 24. End Goal

The ultimate QueryLens pipeline is:

```text
                     USER QUESTION
                           │
                           ▼
                ┌────────────────────┐
                │ Query Understanding │
                └──────────┬─────────┘
                           │
                           ▼
                 Schema Linking
                           │
                           ▼
                Relevant Sub-Schema
                           │
                           ▼
                 SQL Generation
                           │
                           ▼
                  Candidate SQL
                           │
                           ▼
              ┌──────────────────────┐
              │ SQL Validation       │
              │ + Execution          │
              └──────────┬───────────┘
                         │
                    ┌────┴────┐
                    │         │
                  Valid     Invalid
                    │         │
                    │         ▼
                    │      SQL Repair
                    │         │
                    └────┬────┘
                         ▼
                    Final SQL
                         │
                         ▼
                    Evaluation
```

**The immediate next implementation target is hardening `SQLSchemaValidator`:** extend cross-checking to `.joins`, `.filters`, `.aggregations`, and `.group_by` (currently only `.tables` and `.select_columns` are checked). After that: a trained (not zero-shot) schema linker, SFT/GRPO SQL generation, and the self-healing execution agent.
