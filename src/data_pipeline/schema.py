from pyspark.sql.types import(
    StructType,
    StructField,
    StringType,
    BooleanType,
)

QUERY_SCHEMA = StructType([
    StructField("example_id",StringType(),False),
    StructField("source", StringType(), False),
    StructField("domain", StringType(), True),
    StructField("schema_id", StringType(), False),
    StructField("nl_question", StringType(), False),
    StructField("ground_truth_sql", StringType(), False),
    StructField("normalized_sql", StringType(), True),
    StructField("schema_ddl", StringType(), True),
    StructField("dialect", StringType(), True),

    # Processing metadata
    StructField("parse_status", StringType(), True),
    StructField("execution_status", StringType(), True),
    StructField("validation_error", StringType(), True),
])