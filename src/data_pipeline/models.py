"""
models.py — Core in-memory data model for the QueryLens pipeline.

NormalizedQuery is the single shared record type that every stage of the
pipeline produces or consumes.  Using a typed dataclass instead of raw dicts
gives us:
  - IDE auto-complete and static type checking
  - Guaranteed field names across all sources (Spider, BIRD, Synthetic)
  - A trivial path to JSON/JSONL serialization via dataclasses.asdict()

Motivation: the three source datasets use completely different field names and
conventions.  After the adapter + normalizer stages, every record is a
NormalizedQuery — downstream code (splitting, dedup, training) never needs to
know which dataset a record came from.
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Union


@dataclass
class NormalizedQuery:
    """
    One (question, SQL, schema) training example in canonical form.

    Fields
    ------
    id              Unique string identifier within a batch (set to str(index)
                    by the normalizer; replace with a stable UUID in production).
    source          Dataset origin: "spider" | "bird" | "synthetic".
    domain          Semantic domain, e.g. "finance", "ecommerce", "general".
                    Used for domain-aware retrieval and analysis.
    dialect         SQL dialect: "sqlite" | "mysql" | "postgresql" | "duckdb".
                    Critical for query generation — dialects differ in syntax,
                    functions, and type systems.
    database_id     Canonical name of the database/schema.  Used as the
                    grouping key for database-level train/val/test splitting,
                    which prevents schema leakage across splits.
    nl_question     The natural-language question a user would ask.
    ground_truth_sql The correct SQL answer used for supervised training and
                    evaluation.
    ddl             CREATE TABLE statements describing the schema.  Kept as raw
                    text in Phase 1; a schema parser will produce structured
                    tables/columns/relationships in a later phase.
    metadata        Optional pass-through bag for source-specific extras (e.g.
                    difficulty score, original db_id) that don't belong in the
                    canonical schema but may be useful for analysis.
    """

    id: str
    source: str
    domain: str
    dialect: str
    database_id: str
    nl_question: str
    ground_truth_sql: str
    ddl: str
    # Optional extras — not part of the training schema, kept for traceability
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict representation (suitable for JSON serialisation)."""
        return asdict(self)

    def to_json(self) -> str:
        """Return a compact JSON string for a single record."""
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ── File I/O helpers ───────────────────────────────────────────────────────

def save_jsonl(records: list["NormalizedQuery"], path: Union[str, Path]) -> None:
    """
    Write a list of NormalizedQuery records to a .jsonl file.

    JSONL (one JSON object per line) is preferred over a single JSON array
    because it supports streaming reads, easy appending, and trivial sharding
    for large datasets without loading the whole file into memory.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def save_json(records: list["NormalizedQuery"], path: Union[str, Path]) -> None:
    """
    Write a list of NormalizedQuery records to a single pretty-printed .json
    file.  Useful for small datasets or human inspection; prefer save_jsonl
    for large files.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in records], f, ensure_ascii=False, indent=2)