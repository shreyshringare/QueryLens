"""Tests for dialect normalisation in src/data_pipeline/dialects.py."""
import pytest

from src.data_pipeline.dialects import DIALECT_ALIASES, SUPPORTED_DIALECTS, normalize_dialect


# ── Alias mapping ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("alias, expected", [
    ("postgres",    "postgresql"),
    ("postgresql",  "postgresql"),
    ("pg",          "postgresql"),
    ("mysql",       "mysql"),
    ("sqlite",      "sqlite"),
    ("sqlite3",     "sqlite"),
    ("duckdb",      "duckdb"),
])
def test_known_aliases(alias, expected):
    assert normalize_dialect(alias) == expected


# ── Unknown / garbage input → "unknown" ─────────────────────────────────────

@pytest.mark.parametrize("bad", [
    "oracle",
    "mssql",
    "sql_server",
    "",
    "???",
    "bigquery",
])
def test_unknown_dialect_returns_unknown(bad):
    assert normalize_dialect(bad) == "unknown"


# ── Case insensitivity ───────────────────────────────────────────────────────

@pytest.mark.parametrize("alias", [
    "POSTGRES", "PostgreSQL", "SQLite3", "DuckDB", "MySQL",
])
def test_dialect_normalisation_is_case_insensitive(alias):
    result = normalize_dialect(alias)
    assert result in SUPPORTED_DIALECTS


# ── Whitespace stripping ─────────────────────────────────────────────────────

def test_dialect_strips_whitespace():
    assert normalize_dialect("  sqlite  ") == "sqlite"
    assert normalize_dialect("\tpostgres\n") == "postgresql"


# ── All normalised values are in SUPPORTED_DIALECTS ─────────────────────────

def test_all_alias_values_are_supported():
    for canonical in DIALECT_ALIASES.values():
        assert canonical in SUPPORTED_DIALECTS
