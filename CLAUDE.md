# QueryLens 3.0

## What this is
Domain-agnostic, dialect-aware, self-healing NL-to-SQL agent.
Schema-linking agent prunes any DDL to relevant columns.
GRPO-trained Qwen2.5-Coder-7B generates dialect-correct SQL.
SQL Validator catches errors before execution (parse + dialect + schema).
Dialect Adapter transpiles across PostgreSQL / MySQL / SQLite / DuckDB.
Self-healing execution agent retries with error context.
Confidence calibrator routes low-confidence queries to humans.
MCP server exposes four tools. Every step traced via OpenTelemetry.

Domains: Finance, Healthcare, E-commerce, Education, HR, Sports, Entertainment.
Dialects: PostgreSQL, MySQL, SQLite, DuckDB.

## Stack
Python 3.12, Unsloth, TRL, sentence-transformers, sqlglot,
PySpark, DuckDB, Polars, MCP SDK, OpenTelemetry, Jaeger,
Gradio, HF Spaces, Docker Compose

## Commands
# Data
spark-submit data/spark_pipeline/preprocess.py
uv run python data/build_schema_linker_dataset.py
uv run python data/build_sft_dataset.py
uv run python data/build_rlvr_dataset.py

# Training
uv run python agents/train_schema_linker.py
uv run python training/sft/train_sft.py
uv run python training/rlvr/train_grpo.py
uv run python agents/train_confidence_calibrator.py

# Evaluation
uv run python eval/evaluate.py

# Server
uv run python mcp_server/querylens_mcp.py

# Infrastructure
docker compose up -d

# Tests
uv run pytest tests/

## Build order
Phase 0:  Schema registry + 9 schemas across 7 domains + verified pairs
          Gate: 100% of synthetic SQL executes in correct dialect

Phase 1:  Spark ETL with domain + dialect columns
          Gate: quality report shows balanced domain + dialect counts

Phase 2:  Schema linker training
          Gate: top-3 columns hit ground-truth columns on 80%+ of val set

Phase 3:  SQL Validator
          Gate: test_sql_validator.py passes; catches hallucinated table names

Phase 4:  Dialect Adapter
          Gate: test_dialect_adapter.py passes on 20 cross-dialect pairs

Phase 5:  SFT with dialect hints in prompt
          Gate: base vs SFT execution rate per dialect measured

Phase 6:  Reward function + comparator
          Gate: test_reward_function.py passes

Phase 7:  GRPO with error-driven curriculum
          Gate: SFT vs SFT+GRPO exact match per domain measured

Phase 8:  Execution agent
          Gate: retry loop fixes syntax errors 60%+ of the time

Phase 9:  Confidence calibrator
          Gate: calibration curve is monotonic; AUC > 0.75

Phase 10: MCP server — all four tools callable
          Gate: MCP inspector confirms all tools respond correctly

Phase 11: OpenTelemetry — end-to-end trace in Jaeger
          Gate: full pipeline trace visible with all span attributes

Phase 12: Held-out evaluation — per domain, per dialect
          Gate: domain_breakdown.md + comparison_table.md have real numbers

Phase 13: Deployment
          Gate: HF Space live; README has honest numbers

## Key constraints
- NEVER fabricate numbers — every number from evaluate.py
- Held-out schemas MUST be never-seen during SFT or GRPO
- SQL Validator MUST run before execution agent — never skip
- Dialect Adapter MUST run after generation, before execution
- GRPO MUST start from SFT checkpoint
- Reward ordering: timeout(-1.0) < syntax(-0.5) < wrong(0-0.9) < exact(1.0)
- Schema DDL MUST flow as a column through Spark pipeline
- Every agent method MUST be wrapped with @traced decorator
- Confidence routing MUST be configurable threshold, not hardcoded

## Working style
- Small diffs only — no large rewrites without asking
- Conventional commits: feat/fix/test/perf/docs(scope): description
- Never add Claude as co-author in commits
- Compact at ~90% context: restate current phase and file, continue