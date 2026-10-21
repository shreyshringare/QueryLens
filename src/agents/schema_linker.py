from dataclasses import dataclass

from sentence_transformers import CrossEncoder

from src.schema.models import DatabaseSchema, Table


@dataclass
class ColumnScore:
    table: str
    column: str
    score: float


class SchemaLinker:

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L6-v2"):
        self.model = CrossEncoder(model_name)

    def rank(self, question: str, schema: DatabaseSchema) -> list[ColumnScore]:

        candidates = []
        locations = []

        for table in schema.tables:
            for column in table.columns:
                candidates.append(f"{table.name}.{column.name} ({column.data_type})")
                locations.append((table.name, column.name))

        scores = self.model.predict([(question, candidate) for candidate in candidates])

        results = [
            ColumnScore(table=table_name, column=column_name, score=float(score))
            for (table_name, column_name), score in zip(locations, scores)
        ]

        results.sort(key=lambda item: item.score, reverse=True)

        return results

    def select(self, question: str, schema: DatabaseSchema, top_k: int = 3) -> DatabaseSchema:

        top = self.rank(question, schema)[:top_k]

        selected_columns: dict[str, set[str]] = {}

        for item in top:
            selected_columns.setdefault(item.table, set()).add(item.column)

        # Auto-include primary/foreign keys of every selected table, even if the
        # cross-encoder didn't rank them in the top-k — otherwise a pruned-away
        # FK/PK column would make SQLSchemaValidator flag false "unknown column"
        # errors on an otherwise-valid join once SQL referencing it is generated.
        # Known, spec'd limitation: this only preserves a SELECTED table's own
        # PK/FK columns — it does NOT pull in a new table that an FK points to.
        # A selected table's FK column can end up referencing a table absent
        # from the pruned schema (e.g. orders.customer_id survives even if
        # customers wasn't independently selected). Acceptable for this phase;
        # revisit if a downstream consumer needs full referential closure.
        for table in schema.tables:

            if table.name not in selected_columns:
                continue

            for column in table.columns:
                if column.primary_key:
                    selected_columns[table.name].add(column.name)

            for fk in table.foreign_keys:
                selected_columns[table.name].add(fk.column)

        pruned_tables = []

        for table in schema.tables:

            if table.name not in selected_columns:
                continue

            kept_names = selected_columns[table.name]
            kept_columns = [column for column in table.columns if column.name in kept_names]
            kept_foreign_keys = list(table.foreign_keys)

            pruned_tables.append(
                Table(name=table.name, columns=kept_columns, foreign_keys=kept_foreign_keys)
            )

        return DatabaseSchema(database_id=schema.database_id, tables=pruned_tables)
