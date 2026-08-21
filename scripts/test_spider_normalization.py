from src.data_pipeline.adapters.spider import SpiderAdapter
from src.data_pipeline.normalizer import QueryNormalizer


adapter = SpiderAdapter()

normalizer = QueryNormalizer("spider")

raw_record = {
    "question": "How many singers are there?",
    "query": "SELECT COUNT(*) FROM singer",
    "db_id": "concert_singer",
    "ddl": "...",
}

adapted = adapter.adapt(raw_record)

normalized = normalizer.normalize(
    adapted,
    0,
)

print(normalized)