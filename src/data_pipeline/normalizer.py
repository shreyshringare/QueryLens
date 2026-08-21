"""
normalizer.py — Converts adapter output into a typed NormalizedQuery.

The normalizer is the second stage of the two-step transformation:

    raw record
       ↓  (adapter)
    intermediate dict  ← keys unified across sources
       ↓  (normalizer)
    NormalizedQuery    ← typed, validated, ready for downstream use

Why split into adapter + normalizer (not just one step)?
  Adapters are source-specific: they know Spider says "query" and BIRD says
  "SQL".  The normalizer is source-agnostic: once the intermediate dict exists,
  the normalizer does not care where the data came from.  This separation
  means each class has one clear responsibility and can be tested independently.

QueryNormalizer responsibilities:
  1. Extract fields from the intermediate dict with consistent fallback chains.
  2. Raise ValueError early for records that are structurally unusable
     (no question, no SQL) rather than letting bad data propagate silently.
  3. Apply dialect normalisation via normalize_dialect() so downstream code
     always receives a canonical dialect string.
  4. Synthesise a fallback database_id from source + index when none is present.
"""

from typing import Any

from .dialects import normalize_dialect
from .models import NormalizedQuery


class QueryNormalizer:
    """
    Source-aware normalizer that converts an intermediate dict into a
    NormalizedQuery dataclass.

    The `source` constructor argument is used only for:
      - Embedding the source label into the final record.
      - Providing a source-specific default dialect when the record has none.
    """

    def __init__(self, source: str) -> None:
        # Strip and lower-case so "Spider" and " BIRD " are handled correctly
        self.source = source.lower().strip()

    def normalize(
        self,
        record: dict[str, Any],
        index: int,
    ) -> NormalizedQuery:
        """
        Produce a NormalizedQuery from the intermediate adapter dict.

        Parameters
        ----------
        record : dict
            Output of an adapter's .adapt() method.  Expected to contain at
            least "question" (or "nl_question") and "query" (or "sql" /
            "ground_truth_sql").
        index : int
            Position of this record in the current batch.  Used as the record
            id and as a component of the fallback database_id.

        Raises
        ------
        ValueError
            Raised (not silently skipped) when question or SQL are absent.
            The caller (build_normalized_dataset.py) catches this and logs it.
        """
        # ── Natural-language question ──────────────────────────────────────
        # Try the NormalizedQuery-style key first ("nl_question"), then the
        # Spider/BIRD/Synthetic convention ("question").
        question = (
            record.get("nl_question")
            or record.get("question")
        )

        # ── SQL answer ────────────────────────────────────────────────────
        # Try normalised key, then source-specific variants.
        sql = (
            record.get("ground_truth_sql")
            or record.get("sql")
            or record.get("query")
        )

        # Fail fast — a record without a question or SQL is useless for
        # training and should not silently produce an empty NormalizedQuery.
        if not question:
            raise ValueError(
                f"Record {index} is missing a natural-language question"
            )

        if not sql:
            raise ValueError(
                f"Record {index} is missing a SQL query"
            )

        # DDL is optional at this stage (it may be injected by the builder
        # from a sibling schema.sql file before normalize() is called).
        ddl = record.get("ddl") or ""

        # ── Database identifier ───────────────────────────────────────────
        # Prefer "database_id" (canonical), fall back to Spider-style "db_id",
        # then synthesise a unique placeholder so dedup still works correctly.
        database_id = (
            record.get("database_id")
            or record.get("db_id")
            or f"{self.source}_db_{index}"  # last resort — keeps record valid
        )

        # ── Domain ────────────────────────────────────────────────────────
        domain = record.get("domain") or "general"

        # ── Dialect normalisation ─────────────────────────────────────────
        # Read the raw dialect string, run it through the alias table, and
        # fall back to the source-specific default if the result is "unknown".
        # This ensures every record has a recognised dialect.
        raw_dialect = record.get("dialect") or self._default_dialect()
        dialect = normalize_dialect(raw_dialect)
        if dialect == "unknown":
            # normalize_dialect returned "unknown" → alias not in the table.
            # Substitute the source default rather than propagating "unknown".
            dialect = self._default_dialect()

        # Pass-through any extra source-specific fields stored by the adapter
        metadata = dict(record.get("metadata") or {})

        return NormalizedQuery(
            id=str(index),
            source=self.source,
            domain=str(domain),
            dialect=str(dialect),
            database_id=str(database_id),
            nl_question=str(question).strip(),
            ground_truth_sql=str(sql).strip(),
            ddl=str(ddl).strip(),
            metadata=metadata,
        )

    def _default_dialect(self) -> str:
        """
        Return the canonical default dialect for a given source.

        These defaults mirror the adapter conventions:
          Spider    → sqlite  (all Spider databases are SQLite)
          BIRD      → mysql   (most BIRD databases are MySQL)
          Synthetic → duckdb  (QueryLens synthetic workloads target DuckDB)
        """
        if self.source == "spider":
            return "sqlite"
        if self.source == "bird":
            return "mysql"
        if self.source == "synthetic":
            return "duckdb"
        # For future sources with no registered default
        return "unknown"