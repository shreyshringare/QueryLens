import os
import sys
from pathlib import Path

# Ensure PySpark uses current Python executable
os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

import pytest
from pyspark.sql import SparkSession
from src.data_pipeline import load_synthetic, QUERY_SCHEMA


@pytest.fixture(scope="module")
def spark_session():
    spark = (
        SparkSession.builder
        .appName("QueryLensTestPytest")
        .master("local[1]")
        .getOrCreate()
    )
    yield spark
    spark.stop()


def test_load_synthetic_ecommerce(spark_session):
    base_dir = Path("data/raw/synthetic/ecommerce")
    df = load_synthetic(
        spark=spark_session,
        base_dir=base_dir,
        schema_id="ecommerce",
        domain="ecommerce",
        dialect="duckdb",
    )

    assert df is not None
    assert df.count() == 6
    assert df.schema == QUERY_SCHEMA

    row = df.filter(df.example_id == "ecom_001").first()
    assert row is not None
    assert row["source"] == "synthetic"
    assert row["domain"] == "ecommerce"
    assert row["dialect"] == "duckdb"
    assert "customers" in row["schema_ddl"]
    assert "India" in row["ground_truth_sql"]
