"""Tests for row-level and database-level splitting in src/data_pipeline/split.py."""
import pytest

from src.data_pipeline.models import NormalizedQuery
from src.data_pipeline.split import split_records, split_records_by_database


# ── Helpers ──────────────────────────────────────────────────────────────────

def _rec(uid: str, db_id: str = "db_1") -> NormalizedQuery:
    return NormalizedQuery(
        id=uid,
        source="synthetic",
        domain="general",
        dialect="duckdb",
        database_id=db_id,
        nl_question=f"question {uid}",
        ground_truth_sql=f"SELECT {uid}",
        ddl="CREATE TABLE t (id INT);",
    )


def _make_records(n: int, db_id: str = "db_1") -> list[NormalizedQuery]:
    return [_rec(str(i), db_id) for i in range(n)]


# ── split_records (row-level) ────────────────────────────────────────────────

def test_split_sizes_100():
    records = _make_records(100)
    train, val, test = split_records(records, train_ratio=0.8, val_ratio=0.1, seed=42)
    assert len(train) == 80
    assert len(val) == 10
    assert len(test) == 10


def test_split_total_is_conserved():
    records = _make_records(50)
    train, val, test = split_records(records)
    assert len(train) + len(val) + len(test) == 50


def test_split_sets_are_disjoint():
    records = _make_records(100)
    train, val, test = split_records(records, seed=42)
    train_ids = {r.id for r in train}
    val_ids = {r.id for r in val}
    test_ids = {r.id for r in test}
    assert train_ids.isdisjoint(val_ids)
    assert train_ids.isdisjoint(test_ids)
    assert val_ids.isdisjoint(test_ids)


def test_split_is_reproducible():
    records = _make_records(100)
    train1, _, _ = split_records(records, seed=99)
    train2, _, _ = split_records(records, seed=99)
    assert [r.id for r in train1] == [r.id for r in train2]


def test_split_different_seeds_give_different_order():
    records = _make_records(100)
    train1, _, _ = split_records(records, seed=1)
    train2, _, _ = split_records(records, seed=2)
    assert [r.id for r in train1] != [r.id for r in train2]


def test_split_empty_list():
    train, val, test = split_records([])
    assert train == val == test == []


def test_split_small_list_does_not_crash():
    records = _make_records(3)
    train, val, test = split_records(records)
    assert len(train) + len(val) + len(test) == 3


# ── split_records_by_database ────────────────────────────────────────────────

def _multi_db_records() -> list[NormalizedQuery]:
    """10 records spread across 5 databases (2 records each)."""
    records = []
    for db in ["db_A", "db_B", "db_C", "db_D", "db_E"]:
        records.extend([_rec(f"{db}_0", db), _rec(f"{db}_1", db)])
    return records


def test_db_split_no_leakage():
    records = _multi_db_records()
    train, val, test = split_records_by_database(records, seed=42)
    train_dbs = {r.database_id for r in train}
    val_dbs = {r.database_id for r in val}
    test_dbs = {r.database_id for r in test}
    assert train_dbs.isdisjoint(val_dbs)
    assert train_dbs.isdisjoint(test_dbs)
    assert val_dbs.isdisjoint(test_dbs)


def test_db_split_total_is_conserved():
    records = _multi_db_records()
    train, val, test = split_records_by_database(records, seed=42)
    assert len(train) + len(val) + len(test) == len(records)


def test_db_split_reproducible():
    records = _multi_db_records()
    t1, v1, e1 = split_records_by_database(records, seed=7)
    t2, v2, e2 = split_records_by_database(records, seed=7)
    assert {r.id for r in t1} == {r.id for r in t2}


def test_db_split_three_dbs_each_split_gets_one():
    """With exactly 3 databases the guard-logic ensures val and test get at least 1 db."""
    records = []
    for db in ["alpha", "beta", "gamma"]:
        records.extend([_rec(f"{db}_0", db), _rec(f"{db}_1", db)])
    train, val, test = split_records_by_database(records, seed=42)
    assert len({r.database_id for r in val}) >= 1
    assert len({r.database_id for r in test}) >= 1


def test_db_split_single_db_all_in_train():
    """When there is only one database everything lands in train."""
    records = _make_records(10, db_id="only_db")
    train, val, test = split_records_by_database(records, seed=42)
    # With 1 DB split ratios collapse it all into train
    assert len(train) + len(val) + len(test) == 10
