from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT / "data"

RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
INTERIM_DIR = DATA_DIR / "interim"
SCHEMAS_DIR = DATA_DIR / "schemas"

SPIDER_DIR = RAW_DIR / "spider"
BIRD_DIR = RAW_DIR / "bird"
SYNTHETIC_DIR = RAW_DIR / "synthetic"

SPIDER_CAP = 5000

RANDOM_SEED = 50

TRAIN_RATIO = 0.80
VAL_RATIO = 0.10
TEST_RATIO = 0.10