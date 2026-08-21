"""
config.py — Project-wide path and constant definitions.

All file paths in the pipeline are derived from ROOT so the project can be
moved or cloned without touching any other file.  Centralising them here means
a single edit relocates every data directory for the entire codebase.

Motivation: avoid hardcoded path strings scattered across scripts and modules,
which are fragile and error-prone when running from different working
directories.
"""

from pathlib import Path

# Absolute path to the repository root (two levels above this file:
#   src/data_pipeline/config.py → src/ → <root>)
ROOT = Path(__file__).resolve().parents[2]

# Top-level data directory
DATA_DIR = ROOT / "data"

# ── Data tier directories ──────────────────────────────────────────────────
# raw/      → original, unmodified source files (Spider, BIRD, Synthetic)
# processed/→ outputs of the normalization pipeline (normalized.jsonl, splits…)
# interim/  → scratch space for intermediate artefacts (not committed)
# schemas/  → standalone DDL files used when a dataset lacks inline schemas
RAW_DIR       = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
INTERIM_DIR   = DATA_DIR / "interim"
SCHEMAS_DIR   = DATA_DIR / "schemas"

# Per-source raw directories discovered by the dataset builder
SPIDER_DIR    = RAW_DIR / "spider"
BIRD_DIR      = RAW_DIR / "bird"
SYNTHETIC_DIR = RAW_DIR / "synthetic"

# ── Pipeline constants ─────────────────────────────────────────────────────
# SPIDER_CAP limits Spider ingestion so it does not dominate the dataset;
# class imbalance in training data leads to a model that over-fits one dialect.
SPIDER_CAP  = 5000

# A fixed seed makes all shuffle / split operations reproducible across runs.
RANDOM_SEED = 50

# Standard 80 / 10 / 10 split.  Change here to affect every split call that
# reads these constants instead of baking values directly into split calls.
TRAIN_RATIO = 0.80
VAL_RATIO   = 0.10
TEST_RATIO  = 0.10