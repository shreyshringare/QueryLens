import json
from pathlib import Path
from typing import Union

from pyspark.sql import DataFrame, SparkSession

from .schema import QUERY_SCHEMA

__all__ = ["load_jsonl", "load_synthetic"]


def load_jsonl(
    spark: SparkSession,
    path: Union[str, Path],
    source: str,
    domain: str,
    schema_id: str,
    schema_ddl: str,
    dialect: str,
) -> DataFrame:
    path = Path(path)
    records = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            item = json.loads(line)

            nl_question = item.get("question") or item.get("nl_question")
            ground_truth_sql = item.get("sql") or item.get("ground_truth_sql")

            if not nl_question or not ground_truth_sql:
                raise KeyError(
                    f"Record in {path} must contain 'question'/'nl_question' and 'sql'/'ground_truth_sql'."
                )

            records.append({
                "example_id": item.get(
                    "example_id",
                    f"{source}_{schema_id}_{len(records)}"
                ),
                "source": source,
                "domain": domain,
                "schema_id": schema_id,
                "nl_question": nl_question,
                "ground_truth_sql": ground_truth_sql,
                "normalized_sql": item.get("normalized_sql", None),
                "schema_ddl": schema_ddl,
                "dialect": dialect,
                "parse_status": item.get("parse_status", None),
                "execution_status": item.get("execution_status", None),
                "validation_error": item.get("validation_error", None),
            })

    return spark.createDataFrame(records, QUERY_SCHEMA)


def load_synthetic(
    spark: SparkSession,
    base_dir: Union[str, Path],
    schema_id: str,
    domain: str,
    dialect: str,
) -> DataFrame:
    base_dir = Path(base_dir)
    examples_path = base_dir / "examples.jsonl"
    schema_path = base_dir / "schema.sql"

    schema_ddl = schema_path.read_text(encoding="utf-8")

    return load_jsonl(
        spark=spark,
        path=examples_path,
        source="synthetic",
        domain=domain,
        schema_id=schema_id,
        schema_ddl=schema_ddl,
        dialect=dialect,
    )