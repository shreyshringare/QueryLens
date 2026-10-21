from dataclasses import dataclass

from sentence_transformers import CrossEncoder

from src.schema.models import DatabaseSchema


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
