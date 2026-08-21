"""
validation.py — Field-level record validation.

Validation is a separate stage (not part of the normalizer) because its role
is different: the normalizer transforms data, the validator inspects it.

Running validation after normalisation means:
  - We check the canonical NormalizedQuery fields, not source-specific dicts.
  - Validation errors are expressed in terms the rest of the pipeline
    understands ("missing DDL") rather than source jargon ("schema_ddl absent").

Design decision — return a list of errors, not raise on first failure:
  Collecting all errors in one pass lets the dataset builder report exactly how
  many records have missing DDL vs. missing SQL vs. short questions.  This is
  more useful for data quality diagnostics than stopping at the first problem.

Validation intentionally stays simple: it enforces presence and minimum length.
Semantic checks (e.g. "does the SQL parse?", "does it execute?") belong in a
later quality-gate stage that requires a live database connection.
"""

from .models import NormalizedQuery


def validate_record(
    record: NormalizedQuery,
) -> list[str]:
    """
    Inspect a NormalizedQuery for missing or obviously invalid fields.

    Returns a list of human-readable error strings.  An empty list means the
    record passed all checks and is safe to include in the dataset.

    Checks performed
    ----------------
    - Presence of id, source, nl_question, ground_truth_sql, database_id,
      dialect, ddl  (all required for training).
    - Minimum length of nl_question (≥ 3 chars) and ground_truth_sql (≥ 3
      chars) to reject placeholder strings like "q" or "s".

    Parameters
    ----------
    record : NormalizedQuery
        A record that has already passed through the adapter + normalizer.

    Returns
    -------
    list[str]
        Empty if valid.  Otherwise a list of descriptive error strings,
        one per violated constraint.
    """
    errors: list[str] = []

    # ── Required presence checks ──────────────────────────────────────────
    # Each field is critical for a different reason:
    #   id          → needed for deduplication bookkeeping
    #   source      → needed for split statistics and filtering
    #   nl_question → the model input; useless record without it
    #   SQL         → the training label; useless record without it
    #   database_id → needed for database-level splitting (no leakage)
    #   dialect     → model must know the target SQL dialect
    #   ddl         → the schema context fed to the model at inference time
    if not record.id:
        errors.append("missing id")
    if not record.source:
        errors.append("missing source")
    if not record.nl_question:
        errors.append("missing question")
    if not record.ground_truth_sql:
        errors.append("missing SQL")
    if not record.database_id:
        errors.append("missing database_id")
    if not record.dialect:
        errors.append("missing dialect")
    if not record.ddl:
        errors.append("missing DDL")

    # ── Minimum length checks ─────────────────────────────────────────────
    # Catch placeholder strings that pass the presence check but are not
    # real data (e.g. "q", "s", "x" written by mistake during authoring).
    question = record.nl_question.strip()
    if len(question) < 3:
        errors.append("question too short")

    sql = record.ground_truth_sql.strip()
    if len(sql) < 3:
        errors.append("SQL too short")

    return errors
