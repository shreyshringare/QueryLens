from dataclasses import dataclass

from sentence_transformers import CrossEncoder


@dataclass
class ColumnScore:
    table: str
    column: str
    score: float


class SchemaLinker:

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L6-v2"):
        self.model = CrossEncoder(model_name)
