"""
dialects.py — SQL dialect normalisation utilities.

Different datasets use inconsistent names for the same SQL dialect.
Spider uses "sqlite" but some downstream tools call it "sqlite3".
BIRD uses both "mysql" and "MySQL".  Synthetic data may say "postgres"
or "pg" for PostgreSQL.

Normalising all dialect strings to a canonical form before training means:
  - The model sees consistent tokens ("postgresql", not a mix of "postgres"
    / "pg" / "PostgreSQL").
  - Split and statistics code can group records reliably.
  - Adding a new alias only requires a single dict update here.

Motivation: dialect awareness is essential for QueryLens because the same
natural-language question may require syntactically different SQL depending
on the target database.  A model that confuses dialects will generate queries
that fail to execute.
"""

# The set of dialects the pipeline officially recognises.
# Any alias that does not resolve to one of these is mapped to "unknown".
SUPPORTED_DIALECTS = {
    "sqlite",
    "mysql",
    "postgresql",
    "duckdb",
    "unknown",   # sentinel for unsupported / missing dialect information
}


# Maps every known alias → canonical dialect name.
# Add new aliases here as new datasets are integrated; the rest of the
# codebase calls normalize_dialect() and never needs to know about aliases.
DIALECT_ALIASES = {
    # PostgreSQL aliases
    "postgres":   "postgresql",
    "postgresql": "postgresql",
    "pg":         "postgresql",

    # MySQL (no common aliases, kept for completeness)
    "mysql":      "mysql",

    # SQLite aliases
    "sqlite3":    "sqlite",
    "sqlite":     "sqlite",

    # DuckDB (no common aliases)
    "duckdb":     "duckdb",
}


def normalize_dialect(dialect: str) -> str:
    """
    Map a raw dialect string to a canonical name from SUPPORTED_DIALECTS.

    Steps:
      1. Strip surrounding whitespace and lower-case the input so that
         "  POSTGRES  " and "postgres" both resolve correctly.
      2. Look up the result in DIALECT_ALIASES.
      3. Return "unknown" if the value is not in the alias table.

    Examples
    --------
    >>> normalize_dialect("postgres")
    'postgresql'
    >>> normalize_dialect("SQLite3")
    'sqlite'
    >>> normalize_dialect("oracle")
    'unknown'
    """
    # Normalise casing and whitespace before alias lookup
    value = dialect.strip().lower()

    return DIALECT_ALIASES.get(
        value,
        "unknown",  # safe default — downstream can substitute a source default
    )