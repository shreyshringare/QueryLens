"""
split.py — Train / validation / test splitting for NormalizedQuery records.

Why split after deduplication (not before)?
  If you split first and deduplicate within each split, the same record can
  appear in both train and test — a form of data leakage that inflates
  evaluation metrics.  Deduplicating the full dataset first guarantees that
  no record appears in more than one split.

Two splitting strategies are provided:

1. Row-level random split (split_records)
   ----------------------------------------
   Simple random shuffle followed by a ratio-based slice.  Fast and sufficient
   when the dataset is large and well-distributed across databases.

2. Database-level split (split_records_by_database)
   --------------------------------------------------
   Assigns *entire databases* to one split.  If db_A is in train, no record
   from db_A can appear in val or test.

   Why does this matter?
   Every NL-to-SQL example is tied to a schema.  A model that has seen the
   schema for db_A during training essentially memorises its table and column
   names.  Row-level splitting on such a dataset tests only question rephrasing,
   not generalisation to *new schemas*.  Database-level splitting is a much
   harder and more realistic evaluation — it measures whether the model can
   handle schemas it has never seen before, which is the real-world task.

   Recommendation: use database-level splitting for the final benchmark split
   and row-level splitting for fast iteration during development.
"""

import random
from typing import Sequence, TypeVar

from .models import NormalizedQuery

# Generic type var so split_records works on any list (not just NormalizedQuery)
T = TypeVar("T")


def split_records(
    records: Sequence[T],
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    seed: int = 42,
) -> tuple[list[T], list[T], list[T]]:
    """
    Split a sequence into (train, val, test) by randomly shuffling rows.

    The test ratio is implicit: whatever rows remain after train and val are
    taken form the test set.  With the default 0.8 / 0.1 ratios that is 10 %.

    Parameters
    ----------
    records    : Sequence of any type (NormalizedQuery or plain values).
    train_ratio: Fraction of rows going to train.  Default 0.8.
    val_ratio  : Fraction of rows going to val.    Default 0.1.
    seed       : Random seed for reproducibility.  Default 42.

    Returns
    -------
    (train, val, test) — three lists, disjoint, covering all input rows.
    """
    # Work on a copy so we don't mutate the caller's list
    records_list = list(records)

    # Use a seeded Random instance rather than the global random state so
    # calling this function does not affect other random operations in the
    # process (e.g. test isolation).
    random.Random(seed).shuffle(records_list)

    n = len(records_list)

    # Integer slice indices — int() truncates, so the remainder goes to test
    train_end = int(n * train_ratio)
    val_end   = train_end + int(n * val_ratio)

    return (
        records_list[:train_end],           # train
        records_list[train_end:val_end],    # val
        records_list[val_end:],             # test (remainder)
    )


def split_records_by_database(
    records: Sequence[NormalizedQuery],
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    seed: int = 42,
) -> tuple[list[NormalizedQuery], list[NormalizedQuery], list[NormalizedQuery]]:
    """
    Split records so that no database schema appears in more than one split.

    Algorithm
    ---------
    1. Group all records by database_id.
    2. Shuffle the list of unique database IDs with a fixed seed.
    3. Assign the first 80 % of database IDs to train, the next 10 % to val,
       the rest to test.
    4. Collect all records whose database_id is in the assigned set.

    Guard for small datasets (< 3 databases):
    With very few databases the ratio-based slice may produce empty val or test
    sets.  The guard logic ensures val and test each get at least one database
    when 3+ databases are available, preventing silent empty-set bugs.

    Parameters
    ----------
    records    : Sequence[NormalizedQuery] — must have a database_id field.
    train_ratio: Fraction of *databases* assigned to train.
    val_ratio  : Fraction of *databases* assigned to val.
    seed       : Random seed for reproducible database-ID shuffling.

    Returns
    -------
    (train, val, test) — three lists.  Records from the same database always
    appear together in the same split.
    """
    # ── Step 1: group records by database ─────────────────────────────────
    db_groups: dict[str, list[NormalizedQuery]] = {}
    for r in records:
        db_id = r.database_id
        if db_id not in db_groups:
            db_groups[db_id] = []
        db_groups[db_id].append(r)

    # ── Step 2: shuffle unique database IDs ──────────────────────────────
    unique_dbs = list(db_groups.keys())
    random.Random(seed).shuffle(unique_dbs)

    n_dbs = len(unique_dbs)

    # ── Step 3: assign database IDs to splits ─────────────────────────────
    train_end = int(n_dbs * train_ratio)
    val_end   = train_end + int(n_dbs * val_ratio)

    train_dbs: set[str] = set(unique_dbs[:train_end])
    val_dbs:   set[str] = set(unique_dbs[train_end:val_end])
    test_dbs:  set[str] = set(unique_dbs[val_end:])

    # Guard: with small database counts the int() slices can leave val/test
    # empty.  Promote the last DB(s) from train to ensure coverage.
    if n_dbs >= 3:
        if not val_dbs and unique_dbs:
            val_dbs.add(unique_dbs[-2])
            train_dbs.discard(unique_dbs[-2])
        if not test_dbs and unique_dbs:
            test_dbs.add(unique_dbs[-1])
            train_dbs.discard(unique_dbs[-1])

    # ── Step 4: collect records belonging to each database set ────────────
    train_records = [r for r in records if r.database_id in train_dbs]
    val_records   = [r for r in records if r.database_id in val_dbs]
    test_records  = [r for r in records if r.database_id in test_dbs]

    return train_records, val_records, test_records
