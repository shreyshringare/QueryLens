from src.schema.models import DatabaseSchema

from .schema_linker import SchemaLinker


def recall_at_k(
    cases: list[tuple[DatabaseSchema, str, list[tuple[str, str]]]],
    linker: SchemaLinker,
    top_k: int,
) -> float:

    if not cases:
        return 0.0

    hits = 0

    for schema, question, ground_truth in cases:

        ranked = linker.rank(question, schema)
        top = {(item.table, item.column) for item in ranked[:top_k]}

        if all(pair in top for pair in ground_truth):
            hits += 1

    return hits / len(cases)
