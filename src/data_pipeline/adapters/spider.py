"""
adapters/spider.py — Adapter for the Spider Text-to-SQL benchmark.

Spider is one of the largest and most widely-used cross-domain Text-to-SQL
benchmarks.  Its records use:
  - "question" for the natural-language query
  - "query"    for the SQL answer
  - "db_id"    for the database identifier
  - dialect is always SQLite (Spider was built exclusively on SQLite databases)

Adapter responsibility:
  Take a raw Spider dict and emit a normalised intermediate dict whose keys
  are the same across all sources.  This intermediate form is then handed to
  QueryNormalizer which produces the final NormalizedQuery dataclass.

Why a class?
  Using a class (rather than a plain function) makes the SOURCE constant
  introspectable, allows future adapters to share a base class, and makes
  dependency injection and mocking in tests straightforward.
"""

from typing import Any


class SpiderAdapter:

    # Source label that propagates into every NormalizedQuery produced from
    # Spider data.  Used for statistics, filtering, and split bookkeeping.
    SOURCE = "spider"

    def adapt(
        self,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Map a raw Spider record to the canonical intermediate format.

        Key decisions
        -------------
        * dialect is hardcoded to "sqlite" — every Spider database is SQLite,
          so there is no per-record dialect field to read.
        * domain defaults to "general" because Spider does not tag domains;
          this can be enriched later with a domain classifier.
        * metadata preserves the original db_id for traceability.
        """
        return {
            "id":      record.get("id"),
            "question": record.get("question"),
            # Spider calls the SQL column "query", not "sql"
            "query":   record.get("query"),
            "db_id":   record.get("db_id"),
            "ddl":     record.get("ddl"),
            # Spider has no domain annotation; "general" is a safe placeholder
            "domain":  record.get("domain", "general"),
            # Spider is SQLite-only — never read a dialect from the record
            "dialect": "sqlite",
            "metadata": {
                # Keep the raw db_id so downstream analysis can trace back
                # to the original Spider database folder
                "original_db_id": record.get("db_id"),
            },
        }