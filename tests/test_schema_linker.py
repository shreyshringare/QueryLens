from sentence_transformers import CrossEncoder

from src.agents.schema_linker import ColumnScore, SchemaLinker


def test_column_score_holds_values():

    score = ColumnScore(table="customers", column="name", score=-1.5)

    assert score.table == "customers"
    assert score.column == "name"
    assert score.score == -1.5


def test_schema_linker_loads_default_model():

    linker = SchemaLinker()

    assert isinstance(linker.model, CrossEncoder)
