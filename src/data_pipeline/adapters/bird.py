"""
adapters/bird.py — Adapter for the BIRD Text-to-SQL benchmark.

BIRD (Benchmarking the INtelligence of Database systems) focuses on real-world,
dirty databases with external knowledge requirements.  Its schema is less
consistent than Spider and varies between BIRD versions:

  - The question may appear as "question" OR "prompt"
  - The SQL answer may appear as "SQL", "sql", or "query"
  - The database identifier may be "db_id" OR "database_id"
  - Dialect varies per database (MySQL is the most common but not universal)

Adapter responsibility:
  Normalise these inconsistencies into the shared intermediate format so that
  the downstream normalizer and validator never need to know they are handling
  BIRD data.

Motivation: without an adapter layer, every pipeline function would contain
source-specific if/else branches.  Isolating source quirks in their own
adapter class keeps the rest of the pipeline clean and makes it trivial to
add a new source without touching existing code.
"""

from typing import Any


class BIRDAdapter:

    SOURCE = "bird"

    def adapt(
        self,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Map a raw BIRD record to the canonical intermediate format.

        Key decisions
        -------------
        * "question" is preferred over "prompt" — some BIRD versions use
          "prompt" as the question field.
        * "SQL" (uppercase) is the primary SQL field in recent BIRD releases;
          fall back to lowercase "sql" then "query" for older versions.
        * "db_id" is preferred over "database_id" to match Spider's convention
          and simplify the normalizer.
        * Default dialect is "mysql" because most BIRD databases are MySQL.
          Records that carry an explicit "dialect" key override this default.
        """
        return {
            "id": record.get("id"),
            # Prefer "question"; fall back to "prompt" (older BIRD versions)
            "question": (
                record.get("question")
                or record.get("prompt")
            ),
            # Try SQL fields in order of recency/prevalence
            "query": (
                record.get("SQL")       # BIRD 2024+ primary key
                or record.get("sql")    # lowercase variant
                or record.get("query")  # generic fallback
            ),
            # Accept both db_id (Spider convention) and database_id
            "db_id": (
                record.get("db_id")
                or record.get("database_id")
            ),
            # DDL may be absent in BIRD; the builder injects it from schema.sql
            "ddl": record.get("ddl") or "",
            "domain": record.get("domain", "general"),
            # Many BIRD databases are MySQL; records with explicit dialect win
            "dialect": record.get("dialect", "mysql"),
            "metadata": {},
        }