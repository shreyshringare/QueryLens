from typing import Any


class SyntheticAdapter:

    SOURCE = "synthetic"

    def adapt(
        self,
        record: dict[str, Any],
    ) -> dict[str, Any]:

        return {
            "id": record.get("id"),
            "question": (
                record.get("question")
                or record.get("nl_question")
            ),
            "query": (
                record.get("sql")
                or record.get("ground_truth_sql")
            ),
            "db_id": (
                record.get("database_id")
                or record.get("db_id")
                or "synthetic"
            ),
            "ddl": record.get("ddl") or "",
            "domain": record.get(
                "domain",
                "general",
            ),
            "dialect": record.get(
                "dialect",
                "duckdb",
            ),
            "metadata": {},
        }