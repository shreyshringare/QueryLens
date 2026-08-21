"""
dedup.py — Content-based deduplication for NormalizedQuery records.

Why deduplicate?
  Spider and BIRD have overlapping databases.  Community forks and re-releases
  have introduced nearly-identical records across files.  Duplicate examples in
  the training set cause a model to memorise specific question/SQL pairs rather
  than learn to generalise.  Duplicates in the test set inflate accuracy metrics
  by rewarding memorisation.

Strategy — SHA-256 fingerprinting on (question, SQL, database_id):
  The fingerprint is computed on the *content* of the record, not its id or
  file path.  This means:
    - The same question asked about the same database in two different source
      files is treated as one record (cross-source dedup).
    - Case and whitespace differences are normalised before hashing so
      "SELECT COUNT(*) FROM t" and "select count(*) from t" are the same.
    - Two different questions about the same database are NOT duplicates.

Dedup happens after normalisation so we compare canonical field values, not
source-specific raw strings.

Dedup happens before splitting so that near-identical records cannot appear
in both the train set and the test set (leakage).
"""

import hashlib

from .models import NormalizedQuery


def record_fingerprint(record: NormalizedQuery) -> str:
    """
    Compute a stable SHA-256 fingerprint for a NormalizedQuery.

    The fingerprint is derived from the three fields that together uniquely
    identify a training example's *content*:
      - nl_question    : the input to the model
      - ground_truth_sql : the expected output
      - database_id    : the schema context (same Q+SQL on different schemas
                          are distinct examples because the SQL may differ)

    All three values are lower-cased and stripped before hashing so that
    typographic variations don't produce spurious fingerprint mismatches.

    Returns
    -------
    str
        64-character hex string (SHA-256 digest).
    """
    # Concatenate the three content fields with a separator that cannot appear
    # naturally in any of the fields, preventing accidental collisions between
    # (e.g.) question="a||b" and question="a" with sql="b".
    value = (
        record.nl_question.strip().lower()
        + "||"
        + record.ground_truth_sql.strip().lower()
        + "||"
        + record.database_id.strip().lower()
    )

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def deduplicate(
    records: list[NormalizedQuery],
) -> list[NormalizedQuery]:
    """
    Remove duplicate records, keeping only the first occurrence.

    "First occurrence" preserves the order of source processing, which is
    intentional: if Spider and BIRD contain the same record, we keep the
    Spider version (processed first) and discard the BIRD duplicate.

    Parameters
    ----------
    records : list[NormalizedQuery]
        Records to deduplicate.  May contain records from multiple sources.

    Returns
    -------
    list[NormalizedQuery]
        Deduplicated list in the same relative order as the input.
    """
    seen: set[str] = set()  # fingerprints of records already included
    result: list[NormalizedQuery] = []

    for record in records:
        fingerprint = record_fingerprint(record)

        if fingerprint in seen:
            # Exact (or normalised) duplicate — skip it
            continue

        seen.add(fingerprint)
        result.append(record)

    return result