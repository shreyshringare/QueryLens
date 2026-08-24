import json
from dataclasses import asdict
from pathlib import Path

from src.schema.parser import SchemaParser
from src.schema.serializer import schema_to_dict
from src.sql.parser import SQLParser


INPUT = Path("data/processed/normalized.jsonl")
OUTPUT = Path("data/structured/structured.jsonl")


def transform_record(record: dict) -> dict:

    database_id = record["database_id"]
    dialect = record.get("dialect")
    ddl = record.get("ddl", "")
    sql = record["ground_truth_sql"]

    schema = SchemaParser(dialect=dialect).parse(
        database_id=database_id,
        ddl=ddl,
    )

    sql_structure = SQLParser(dialect=dialect).parse(sql)

    output = dict(record)
    output["schema"] = schema_to_dict(schema)
    output["sql_structure"] = asdict(sql_structure)

    return output


def main():

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with (
        INPUT.open("r", encoding="utf-8") as source,
        OUTPUT.open("w", encoding="utf-8") as target,
    ):

        for line in source:

            record = json.loads(line)
            output = transform_record(record)

            target.write(json.dumps(output, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
