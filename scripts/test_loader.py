import os
import sys

# Force Spark to use the same Python interpreter as this virtual environment
python_executable = sys.executable
os.environ["PYSPARK_PYTHON"] = python_executable
os.environ["PYSPARK_DRIVER_PYTHON"] = python_executable

from pyspark.sql import SparkSession

from src.data_pipeline.loaders import load_synthetic
from pathlib import Path


spark = (
    SparkSession.builder
    .appName("QueryLensTest")
    .master("local[*]")
    .getOrCreate()
)

df = load_synthetic(
    spark=spark,
    base_dir=Path("data/raw/synthetic/ecommerce"),
    schema_id="ecommerce",
    domain="ecommerce",
    dialect="duckdb",
)

df.show(truncate=False)
df.printSchema()

spark.stop()