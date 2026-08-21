from pathlib import Path
from typing import Any

from .models import NormalizedQuery

class QueryNormalizer:

    def __init__(self,source:str):
        self.source = source.lower().strip()

    def normalize(
        self,
        record : dict[str,Any],
        index : int,
    )->NormalizedQuery:
        question = (
            record.get("nl_question")
            or record.get("question")
        )

        sql = (
            record.get("ground_truth_sql")
            or record.get("sql")
            or record.get("query")
        )

        if not question:
            raise ValueError(
                f"Record {index} is missing a natural-language question"
            )

        if not sql:
            raise ValueError(
                f"Record {index} is missing a SQL query"
            )

        ddl = record.get("ddl") or ""

        database_id = (
            record.get("database_id")
            or record.get("db_id")
            or f"{self.source}_db_{index}"
        )

        domain = (
            record.get("domain")
            or "general"
        )
        
        dialect = (
            record.get("dialect")
            or self._default_dialect()
        )

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

        if self.source == "spider":
            return "sqlite"

        if self.source == "bird":
            return "mysql"

        if self.source == "synthetic":
            return "duckdb"

        return "unknown"