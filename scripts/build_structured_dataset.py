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

    processed = 0
    failed = 0

    with (
        INPUT.open("r", encoding="utf-8") as source,
        OUTPUT.open("w", encoding="utf-8") as target,
    ):

        for index, line in enumerate(source):

            record = json.loads(line)

            try:
                output = transform_record(record)
            except Exception as e:
                print(f"Failed record {index} (id={record.get('id')}): {e}")
                failed += 1
                continue

            target.write(json.dumps(output, ensure_ascii=False) + "\n")
            processed += 1

    print(f"Wrote {processed} records to {OUTPUT} ({failed} failed)")


if __name__ == "__main__":
    main()
